import asyncio
import json
import sqlite3
import time
import uuid
from typing import Annotated, Dict, List, Optional
from ai_prompter import Prompter
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from loguru import logger
from typing_extensions import TypedDict
from open_notebook.ai.provision import provision_langchain_model
from open_notebook.config import LANGGRAPH_CHECKPOINT_FILE
from open_notebook.domain.notebook import Source, SourceInsight
from open_notebook.exceptions import OpenNotebookError
from open_notebook.utils import clean_thinking_content
from open_notebook.utils.context_builder import ContextBuilder
from open_notebook.utils.error_classifier import classify_error
from open_notebook.utils.text_utils import extract_text_content

class SourceChatState(TypedDict):
    messages: Annotated[list, add_messages]
    source_id: str
    source: Optional[Source]
    insights: Optional[List[SourceInsight]]
    context: Optional[str]
    model_override: Optional[str]
    context_indicators: Optional[Dict[str, List[str]]]
    entity_details: Optional[Dict[str, str]]

def _log(level, request_id, stage, **kwargs):
    record = {"request_id": request_id, "stage": stage, **kwargs}
    msg = json.dumps(record, ensure_ascii=False, default=str)
    getattr(logger, level.lower(), logger.info)(msg)

def extract_entities_from_message(message_content):
    import re
    entities = list(re.findall(r"(\w+\s*@\s*\w+|\w+@\w+)", message_content))
    entities += list(re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", message_content))
    return list(set(entities))

def extract_entity_details_from_content(entity_name, content, max_chars=500):
    if not content or not entity_name:
        return None
    import re
    pattern = r"[^.!?]*" + re.escape(entity_name) + r"[^.!?]*[.!?]"
    sentences = [m.group(0).strip() for m in re.finditer(pattern, content, re.IGNORECASE)]
    if not sentences:
        return None
    details = " ".join(sentences)
    return (details[:max_chars] + "...") if len(details) > max_chars else details

def call_model_with_source_context(state, config):
    try:
        return _call_model_with_source_context_inner(state, config)
    except OpenNotebookError:
        raise
    except Exception as e:
        error_class, user_message = classify_error(e)
        raise error_class(user_message) from e

def _call_model_with_source_context_inner(state, config):
    request_id = str(uuid.uuid4())[:8]
    pipeline_start = time.time()
    source_id = state.get("source_id")
    if not source_id:
        raise ValueError("source_id is required in state")
    messages = state.get("messages", [])
    latest_user_message = next((m.content for m in reversed(messages) if isinstance(m, HumanMessage)), None)
    entities = extract_entities_from_message(latest_user_message or "")
    q_lower = (latest_user_message or "").lower()
    question_words = ["what","who","when","where","how","why","which","list","describe","explain"]
    detected_intent = next((w for w in question_words if q_lower.startswith(w)), "statement")
    _log("info", request_id, "QUERY_RECEIVED", source_id=source_id, question=latest_user_message,
         question_length=len(latest_user_message or ""), detected_intent=detected_intent,
         detected_entities=entities, conversation_turns=sum(1 for m in messages if isinstance(m, HumanMessage)))
    retrieval_start = time.time()
    def build_context():
        new_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(new_loop)
            cb = ContextBuilder(source_id=source_id, include_insights=True, include_notes=False, max_tokens=50000)
            return new_loop.run_until_complete(cb.build())
        finally:
            new_loop.close()
            asyncio.set_event_loop(None)
    try:
        asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as ex:
            context_data = ex.submit(build_context).result()
    except RuntimeError:
        context_data = build_context()
    retrieval_time = round(time.time() - retrieval_start, 3)
    sources_retrieved = context_data.get("sources", [])
    insights_retrieved = context_data.get("insights", [])
    full_text_len = sum(len(s.get("full_text","") or "") for s in sources_retrieved if isinstance(s, dict))
    _log("info", request_id, "RETRIEVAL_COMPLETE", retrieval_time_sec=retrieval_time,
         sources_retrieved=len(sources_retrieved),
         source_titles=[s.get("title") if isinstance(s,dict) else str(s) for s in sources_retrieved],
         insights_retrieved=len(insights_retrieved),
         insight_types=[i.get("insight_type") if isinstance(i,dict) else str(i) for i in insights_retrieved],
         total_full_text_chars=full_text_len)
    if not sources_retrieved:
        _log("warning", request_id, "RETRIEVAL_EMPTY", message="No sources retrieved")
    source = None
    insights = []
    context_indicators = {"sources": [], "insights": [], "notes": []}
    if sources_retrieved:
        si = sources_retrieved[0]
        source = Source(**si) if isinstance(si, dict) else si
        context_indicators["sources"].append(source.id)
    for id_ in insights_retrieved:
        if isinstance(id_, dict):
            # Map "type" key to "insight_type" if needed
            if "type" in id_ and "insight_type" not in id_:
                id_ = {**id_, "insight_type": id_["type"]}
            ins = SourceInsight(**id_)
        else:
            ins = id_
        insights.append(ins)
        context_indicators["insights"].append(ins.id)
    formatted_context = _format_source_context(context_data)
    context_chars = len(formatted_context)
    was_truncated = full_text_len > 40000
    _log("info", request_id, "CONTEXT_CONSTRUCTED", context_chars=context_chars,
         sources_included=len(context_indicators["sources"]),
         insights_included=len(context_indicators["insights"]), full_text_truncated=was_truncated)
    if was_truncated:
        _log("warning", request_id, "CONTEXT_TRUNCATED", original_chars=full_text_len,
             truncated_to=40000, chars_lost=full_text_len-40000)
    prompt_data = {"source": source.model_dump() if source else None,
                   "insights": [i.model_dump() for i in insights] if insights else [],
                   "context": formatted_context, "context_indicators": context_indicators}
    system_prompt = Prompter(prompt_template="source_chat/system").render(data=prompt_data)
    payload = [SystemMessage(content=system_prompt)] + messages
    payload_str = str(payload)
    payload_len = len(payload_str)
    dynamic_max_tokens = 32000 if payload_len > 60000 else (16000 if payload_len > 30000 else 12000)
    model_id = config.get("configurable", {}).get("model_id") or state.get("model_override")
    _log("info", request_id, "MODEL_GENERATION_START", model_id=model_id or "default",
         temperature=0.2, max_tokens=dynamic_max_tokens, payload_chars=payload_len,
         system_prompt_chars=len(system_prompt))
    generation_start = time.time()
    def run_in_new_loop():
        new_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(new_loop)
            return new_loop.run_until_complete(
                provision_langchain_model(payload_str, model_id, "chat",
                                          max_tokens=dynamic_max_tokens, temperature=0.2))
        finally:
            new_loop.close()
            asyncio.set_event_loop(None)
    try:
        asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as ex:
            model = ex.submit(run_in_new_loop).result()
    except RuntimeError:
        model = asyncio.run(provision_langchain_model(payload_str, model_id, "chat",
                                                       max_tokens=dynamic_max_tokens, temperature=0.2))
    ai_message = model.invoke(payload)
    generation_time = round(time.time() - generation_start, 3)
    content = extract_text_content(ai_message.content)
    cleaned_content = clean_thinking_content(content)
    cleaned_message = ai_message.model_copy(update={"content": cleaned_content})
    response_words = len(cleaned_content.split())
    token_usage = {}
    if hasattr(ai_message, "usage_metadata") and ai_message.usage_metadata:
        token_usage = {"prompt_tokens": ai_message.usage_metadata.get("input_tokens",0),
                       "completion_tokens": ai_message.usage_metadata.get("output_tokens",0)}
    elif hasattr(ai_message, "response_metadata"):
        usage = (ai_message.response_metadata or {}).get("token_usage") or {}
        token_usage = {"prompt_tokens": usage.get("prompt_tokens",0),
                       "completion_tokens": usage.get("completion_tokens",0)}
    _log("info", request_id, "MODEL_GENERATION_COMPLETE", generation_time_sec=generation_time,
         response_chars=len(cleaned_content), response_words=response_words, **token_usage)
    if response_words < 30:
        _log("warning", request_id, "SHORT_RESPONSE", response_words=response_words,
             message="Response very short - check retrieval/prompt")
    cited_sources = [source.id] if source and source.id and source.id in cleaned_content else []
    cited_insights = [i.id for i in insights if i.id and i.id in cleaned_content]
    total_avail = len(context_indicators["sources"]) + len(context_indicators["insights"])
    util_pct = round(100*(len(cited_sources)+len(cited_insights))/total_avail,1) if total_avail else 0
    _log("info", request_id, "SOURCE_UTILISATION",
         sources_available=len(context_indicators["sources"]),
         insights_available=len(context_indicators["insights"]),
         sources_cited=len(cited_sources), insights_cited=len(cited_insights), utilisation_pct=util_pct)
    entity_details = {}
    if latest_user_message and source and source.full_text:
        for entity in entities:
            details = extract_entity_details_from_content(entity, source.full_text)
            if details:
                entity_details[entity] = details
    _log("debug", request_id, "ENTITY_EXTRACTION", entities_detected=entities,
         entities_found=list(entity_details.keys()))
    total_time = round(time.time() - pipeline_start, 3)
    _log("info", request_id, "PIPELINE_COMPLETE", total_time_sec=total_time,
         retrieval_time_sec=retrieval_time, generation_time_sec=generation_time,
         context_chars=context_chars, response_words=response_words,
         sources_used=len(sources_retrieved), insights_used=len(insights_retrieved))
    return {"messages": cleaned_message, "source": source, "insights": insights,
            "context": formatted_context, "context_indicators": context_indicators,
            "entity_details": entity_details if entity_details else None}

def _format_source_context(context_data):
    parts = []
    if context_data.get("sources"):
        parts.append("## SOURCE CONTENT")
        for s in context_data["sources"]:
            if isinstance(s, dict):
                parts.append(f"**Source ID:** {s.get('id','Unknown')}")
                parts.append(f"**Title:** {s.get('title','No title')}")
                if s.get("full_text"):
                    ft = s["full_text"]
                    if len(ft) > 40000:
                        ft = ft[:40000] + "\n[Content continues beyond this point]"
                    parts.append(f"**Content:**\n{ft}")
                parts.append("")
    if context_data.get("insights"):
        parts.append("\n## GENERATED INSIGHTS FROM THIS SOURCE")
        for i in context_data["insights"]:
            if isinstance(i, dict) and i.get("content"):
                parts.append(f"\n### {i.get('insight_type','Unknown')}")
                parts.append(i["content"])
                parts.append("")
    return "\n".join(parts)

conn = sqlite3.connect(LANGGRAPH_CHECKPOINT_FILE, check_same_thread=False)
memory = SqliteSaver(conn)
source_chat_state = StateGraph(SourceChatState)
source_chat_state.add_node("source_chat_agent", call_model_with_source_context)
source_chat_state.add_edge(START, "source_chat_agent")
source_chat_state.add_edge("source_chat_agent", END)
source_chat_graph = source_chat_state.compile(checkpointer=memory)


