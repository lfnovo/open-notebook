import operator
from typing import Annotated, Any, List

from ai_prompter import Prompter
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from open_notebook.ai.provision import provision_langchain_model
from open_notebook.database.repositories.share_repository import ShareRepository
from open_notebook.domain.notebook import Note, Source, graph_search, vector_search
from open_notebook.exceptions import OpenNotebookError
from open_notebook.utils import clean_thinking_content
from open_notebook.utils.error_classifier import classify_error
from open_notebook.utils.text_utils import extract_text_content


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


def _search_scope(config: RunnableConfig) -> dict[str, Any]:
    scope = config.get("configurable", {}).get("search_scope") or {}
    return scope if isinstance(scope, dict) else {}


def _result_resource_ref(result: dict[str, Any]) -> tuple[str, str] | None:
    for key in ("source_id", "parent_id", "id"):
        value = result.get(key)
        if value is None:
            continue
        value_str = str(value)
        if value_str.startswith("source:"):
            return "source", value_str
        if value_str.startswith("note:"):
            return "note", value_str
    return None


async def _resource_access_metadata(
    resource_type: str,
    resource_id: str,
) -> tuple[str | None, str | None, str]:
    if resource_type == "source":
        source = await Source.get(resource_id)
        if not source:
            return None, None, "private"
        return (
            str(source.owner_id) if source.owner_id else None,
            str(source.workspace_id) if source.workspace_id else None,
            source.visibility,
        )

    note = await Note.get(resource_id)
    if not note:
        return None, None, "private"
    return (
        str(note.owner_id) if note.owner_id else None,
        str(note.workspace_id) if note.workspace_id else None,
        "private",
    )


async def _result_visible_in_scope(
    result: dict[str, Any],
    scope: dict[str, Any],
) -> bool:
    resource_ref = _result_resource_ref(result)
    if not resource_ref:
        return False

    resource_type, resource_id = resource_ref
    owner_id, workspace_id, visibility = await _resource_access_metadata(
        resource_type,
        resource_id,
    )
    actor_id = scope.get("actor_id")
    team_ids = [str(team_id) for team_id in scope.get("team_ids", [])]
    workspace_ids = [str(workspace_id) for workspace_id in scope.get("workspace_ids", [])]

    if scope.get("actor_role") == "admin":
        return True
    if visibility == "public":
        return True
    if actor_id and owner_id == actor_id:
        return True
    if workspace_id and workspace_id in workspace_ids:
        return True
    return await ShareRepository.has_read_grant(
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=actor_id,
        team_ids=team_ids,
    )


async def _filter_results_for_scope(
    results: list[dict[str, Any]],
    scope: dict[str, Any],
) -> list[dict[str, Any]]:
    filtered = []
    for result in results:
        if await _result_visible_in_scope(result, scope):
            filtered.append(result)
    return filtered


async def call_model_with_messages(state: ThreadState, config: RunnableConfig) -> dict:
    try:
        parser = PydanticOutputParser(pydantic_object=Strategy)
        system_prompt = Prompter(prompt_template="ask/entry", parser=parser).render(  # type: ignore[arg-type]
            data=state  # type: ignore[arg-type]
        )
        model = await provision_langchain_model(
            system_prompt,
            config.get("configurable", {}).get("strategy_model"),
            "tools",
            team_id=config.get("configurable", {}).get("team_id"),
            max_tokens=2000,
            streaming=True,
        )
        # model = model.bind_tools(tools)
        # First get the raw response from the model
        ai_message = await model.ainvoke(system_prompt)

        # Clean the thinking content from the response
        message_content = extract_text_content(ai_message.content)
        cleaned_content = clean_thinking_content(message_content)

        # Parse the cleaned JSON content
        strategy = parser.parse(cleaned_content)

        return {"strategy": strategy}
    except OpenNotebookError:
        raise
    except Exception as e:
        error_class, user_message = classify_error(e)
        raise error_class(user_message) from e


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
    import os
    try:
        payload = state
        
        # Perform vector search
        vector_results = await vector_search(state["term"], 10, True, True)
        
        # Check if Knowledge Graph is enabled
        enable_kg = os.environ.get("ENABLE_KNOWLEDGE_GRAPH", "false").lower() == "true"
        graph_results = []
        if enable_kg:
            graph_results = await graph_search(state["term"], 3)
            
        results = await _filter_results_for_scope(
            vector_results + graph_results,
            _search_scope(config),
        )

        if len(results) == 0:
            return {"answers": []}
            
        # 强制把 id 以 'note:' 开头的结果排在最前面
        results = sorted(results, key=lambda x: str(x.get("id", "")).startswith("note:"), reverse=True)
            
        payload["results"] = results
        ids = [r["id"] for r in results]
        payload["ids"] = ids
        system_prompt = Prompter(prompt_template="ask/query_process").render(data=payload)  # type: ignore[arg-type]
        model = await provision_langchain_model(
            system_prompt,
            config.get("configurable", {}).get("answer_model"),
            "tools",
            team_id=config.get("configurable", {}).get("team_id"),
            max_tokens=2000,
        )
        ai_message = await model.ainvoke(system_prompt)
        ai_content = extract_text_content(ai_message.content)
        return {"answers": [clean_thinking_content(ai_content)]}
    except OpenNotebookError:
        raise
    except Exception as e:
        error_class, user_message = classify_error(e)
        raise error_class(user_message) from e


async def write_final_answer(state: ThreadState, config: RunnableConfig) -> dict:
    try:
        system_prompt = Prompter(prompt_template="ask/final_answer").render(data=state)  # type: ignore[arg-type]
        model = await provision_langchain_model(
            system_prompt,
            config.get("configurable", {}).get("final_answer_model"),
            "tools",
            team_id=config.get("configurable", {}).get("team_id"),
            max_tokens=2000,
        )
        ai_message = await model.ainvoke(system_prompt)
        final_content = extract_text_content(ai_message.content)
        return {"final_answer": clean_thinking_content(final_content)}
    except OpenNotebookError:
        raise
    except Exception as e:
        error_class, user_message = classify_error(e)
        raise error_class(user_message) from e


agent_state = StateGraph(ThreadState)
agent_state.add_node("agent", call_model_with_messages)
agent_state.add_node("provide_answer", provide_answer)
agent_state.add_node("write_final_answer", write_final_answer)
agent_state.add_edge(START, "agent")
agent_state.add_conditional_edges("agent", trigger_queries, ["provide_answer"])
agent_state.add_edge("provide_answer", "write_final_answer")
agent_state.add_edge("write_final_answer", END)

graph = agent_state.compile()
