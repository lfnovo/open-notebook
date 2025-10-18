from ai_prompter import Prompter
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from open_notebook.domain.notebook import Source
from open_notebook.domain.transformation import DefaultPrompts, Transformation
from open_notebook.graphs.utils import provision_langchain_model
from open_notebook.utils import clean_thinking_content


class TransformationState(TypedDict):
    input_text: str
    source: Source
    transformation: Transformation
    output: str


async def run_transformation(state: dict, config: RunnableConfig) -> dict:
    source_obj = state.get("source")
    source: Source = source_obj if isinstance(source_obj, Source) else None  # type: ignore[assignment]
    content = state.get("input_text")
    assert source or content, "No content to transform"
    transformation: Transformation = state["transformation"]
    if not content:
        content = source.full_text
    transformation_template_text = transformation.prompt
    default_prompts: DefaultPrompts = DefaultPrompts(transformation_instructions=None)
    if default_prompts.transformation_instructions:
        transformation_template_text = f"{default_prompts.transformation_instructions}\n\n{transformation_template_text}"

    transformation_template_text = f"{transformation_template_text}\n\n# INPUT"

    system_prompt = Prompter(template_text=transformation_template_text).render(
        data=state
    )
    content_str = str(content) if content else ""
    payload = [SystemMessage(content=system_prompt), HumanMessage(content=content_str)]
    chain = await provision_langchain_model(
        str(payload),
        config.get("configurable", {}).get("model_id"),
        "transformation",
        max_tokens=5055,
    )

    response = await chain.ainvoke(payload)

    # Clean thinking content from the response
    response_content = response.content if isinstance(response.content, str) else str(response.content)
    cleaned_content = clean_thinking_content(response_content)

    if source:
        await source.add_insight(transformation.title, cleaned_content)

    return {
        "output": cleaned_content,
    }


agent_state = StateGraph(TransformationState)
agent_state.add_node("agent", run_transformation)  # type: ignore[type-var]
agent_state.add_edge(START, "agent")
agent_state.add_edge("agent", END)
graph = agent_state.compile()
