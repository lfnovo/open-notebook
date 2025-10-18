import operator
from typing import Annotated, List

from ai_prompter import Prompter
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from open_notebook.domain.notebook import vector_search
from open_notebook.graphs.utils import provision_langchain_model
from open_notebook.utils import clean_thinking_content


class SubGraphState(TypedDict):
    question: str
    term: str
    instructions: str
    results: dict
    answer: str
    ids: list  # Added for provide_answer function


class Search(BaseModel):
    term: str
    instructions: str = Field(
        description="Tell the answeting LLM what information you need extracted from this search"
    )


class Strategy(BaseModel):
    reasoning: str
    searches: List[Search] = Field(
        default_factory=list,
        description="You can add up to five searches to this strategy",
    )


class ThreadState(TypedDict):
    question: str
    strategy: Strategy
    answers: Annotated[list, operator.add]
    final_answer: str


async def call_model_with_messages(state: ThreadState, config: RunnableConfig) -> dict:
    parser = PydanticOutputParser(pydantic_object=Strategy)
    system_prompt = Prompter(prompt_template="ask/entry", parser=parser).render(  # type: ignore[arg-type]
        data=state  # type: ignore[arg-type]
    )
    model = await provision_langchain_model(
        system_prompt,
        config.get("configurable", {}).get("strategy_model"),
        "tools",
        max_tokens=2000,
        structured=dict(type="json"),
    )
    # model = model.bind_tools(tools)
    # First get the raw response from the model
    ai_message = await model.ainvoke(system_prompt)

    # Clean the thinking content from the response
    message_content = ai_message.content if isinstance(ai_message.content, str) else str(ai_message.content)
    cleaned_content = clean_thinking_content(message_content)

    # Parse the cleaned JSON content
    strategy = parser.parse(cleaned_content)

    return {"strategy": strategy}


async def trigger_queries(state: ThreadState, config: RunnableConfig):
    return [
        Send(
            "provide_answer",
            {
                "question": state["question"],
                "instructions": s.instructions,
                "term": s.term,
                # "type": s.type,
            },
        )
        for s in state["strategy"].searches
    ]


async def provide_answer(state: SubGraphState, config: RunnableConfig) -> dict:
    payload = state
    # if state["type"] == "text":
    #     results = text_search(state["term"], 10, True, True)
    # else:
    results = await vector_search(state["term"], 10, True, True)
    if len(results) == 0:
        return {"answers": []}
    payload["results"] = results
    ids = [r["id"] for r in results]
    payload["ids"] = ids
    system_prompt = Prompter(prompt_template="ask/query_process").render(data=payload)  # type: ignore[arg-type]
    model = await provision_langchain_model(
        system_prompt,
        config.get("configurable", {}).get("answer_model"),
        "tools",
        max_tokens=2000,
    )
    ai_message = await model.ainvoke(system_prompt)
    ai_content = ai_message.content if isinstance(ai_message.content, str) else str(ai_message.content)
    return {"answers": [clean_thinking_content(ai_content)]}


async def write_final_answer(state: ThreadState, config: RunnableConfig) -> dict:
    system_prompt = Prompter(prompt_template="ask/final_answer").render(data=state)  # type: ignore[arg-type]
    model = await provision_langchain_model(
        system_prompt,
        config.get("configurable", {}).get("final_answer_model"),
        "tools",
        max_tokens=2000,
    )
    ai_message = await model.ainvoke(system_prompt)
    final_content = ai_message.content if isinstance(ai_message.content, str) else str(ai_message.content)
    return {"final_answer": clean_thinking_content(final_content)}


agent_state = StateGraph(ThreadState)
agent_state.add_node("agent", call_model_with_messages)
agent_state.add_node("provide_answer", provide_answer)
agent_state.add_node("write_final_answer", write_final_answer)
agent_state.add_edge(START, "agent")
agent_state.add_conditional_edges("agent", trigger_queries, ["provide_answer"])
agent_state.add_edge("provide_answer", "write_final_answer")
agent_state.add_edge("write_final_answer", END)

graph = agent_state.compile()
