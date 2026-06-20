"""Repo-review graph: a deep-research engine pointed inward.

Mirrors the `ask` graph (distill -> parallel probes -> synthesize), but instead of
answering a question it grades a local code repository against best practices
distilled from the user's own trusted sources.

  1. distill   — vector-search the library for what the sources say about the theme,
                 then have the LLM produce a GuidanceBrief: principles, each with
                 regex `code_probes` and source citations.
  2. probe      — per principle, grep the repo for its probes and have the LLM judge
                 the evidence into a Finding (verdict + path:line evidence).
  3. synthesize — combine findings into a Markdown report citing both sources and code.
"""

import asyncio
import operator
from pathlib import Path
from typing import Annotated, List, Literal

from ai_prompter import Prompter
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from open_notebook.ai.provision import provision_langchain_model
from open_notebook.domain.notebook import vector_search
from open_notebook.exceptions import OpenNotebookError
from open_notebook.utils import clean_thinking_content
from open_notebook.utils.error_classifier import classify_error
from open_notebook.utils.repo_scan import build_file_tree, grep_repo
from open_notebook.utils.text_utils import extract_text_content

# How much of the repo file tree to show the LLM for orientation.
MAX_TREE_LINES = 200


class Principle(BaseModel):
    statement: str = Field(description="The best-practice expectation, one sentence")
    rationale: str = Field(default="", description="Why it matters, per the sources")
    source_citations: List[str] = Field(
        default_factory=list, description="Exact document ids this is drawn from"
    )
    code_probes: List[str] = Field(
        default_factory=list,
        description="Case-insensitive regex patterns that surface relevant code",
    )


class GuidanceBrief(BaseModel):
    theme_summary: str = Field(
        default="", description="One-paragraph summary of what the sources say"
    )
    principles: List[Principle] = Field(default_factory=list)


class Finding(BaseModel):
    verdict: Literal["follows", "partial", "violates", "not-found"]
    summary: str = Field(default="", description="1-3 sentence judgement")
    evidence: List[str] = Field(
        default_factory=list, description="Concrete path:line references"
    )
    recommendation: str = Field(default="", description="Actionable fix, if any")


class ReviewState(TypedDict):
    theme: str
    repo_path: str
    notebook_id: str
    brief: GuidanceBrief
    file_tree: str
    findings: Annotated[list, operator.add]
    report: str


class ProbeState(TypedDict):
    theme: str
    repo_path: str
    file_tree: str
    principle: Principle


def _truncate_tree(files: List[str]) -> str:
    if not files:
        return "(no reviewable files found)"
    shown = files[:MAX_TREE_LINES]
    text = "\n".join(shown)
    if len(files) > MAX_TREE_LINES:
        text += f"\n... ({len(files) - MAX_TREE_LINES} more files not shown)"
    return text


def _format_hits(hits) -> str:
    if not hits:
        return "(no matches found for this principle's probe patterns)"
    blocks = []
    for h in hits:
        blocks.append(f"{h.file}:{h.line}\n{h.snippet}")
    return "\n\n".join(blocks)


async def distill_guidance(state: ReviewState, config: RunnableConfig) -> dict:
    try:
        parser = PydanticOutputParser(pydantic_object=GuidanceBrief)
        results = await vector_search(state["theme"], 15, True, True)
        ids = [r["id"] for r in results]
        payload = {
            "theme": state["theme"],
            "results": results,
            "ids": ids,
        }
        system_prompt = Prompter(prompt_template="repo_review/distill", parser=parser).render(  # type: ignore[arg-type]
            data=payload  # type: ignore[arg-type]
        )
        model = await provision_langchain_model(
            system_prompt,
            config.get("configurable", {}).get("strategy_model"),
            "tools",
            max_tokens=3000,
            structured=dict(type="json"),
        )
        ai_message = await model.ainvoke(system_prompt)
        cleaned = clean_thinking_content(extract_text_content(ai_message.content))
        brief = parser.parse(cleaned)

        # Build the repo file tree once (sync I/O off the event loop).
        files = await asyncio.to_thread(build_file_tree, Path(state["repo_path"]))
        return {"brief": brief, "file_tree": _truncate_tree(files)}
    except OpenNotebookError:
        raise
    except Exception as e:
        error_class, user_message = classify_error(e)
        raise error_class(user_message) from e


def trigger_probes(state: ReviewState, config: RunnableConfig):
    principles = state["brief"].principles if state.get("brief") else []
    if not principles:
        # No principles distilled (e.g. the library has nothing on this theme):
        # skip straight to synthesis, which will say so.
        return ["synthesize_report"]
    return [
        Send(
            "probe_principle",
            {
                "theme": state["theme"],
                "repo_path": state["repo_path"],
                "file_tree": state["file_tree"],
                "principle": principle,
            },
        )
        for principle in principles
    ]


async def probe_principle(state: ProbeState, config: RunnableConfig) -> dict:
    try:
        principle = state["principle"]
        hits = await asyncio.to_thread(
            grep_repo, Path(state["repo_path"]), principle.code_probes
        )
        payload = {
            "theme": state["theme"],
            "principle": principle,
            "file_tree": state["file_tree"],
            "hits": _format_hits(hits),
        }
        parser = PydanticOutputParser(pydantic_object=Finding)
        system_prompt = Prompter(prompt_template="repo_review/judge", parser=parser).render(  # type: ignore[arg-type]
            data=payload  # type: ignore[arg-type]
        )
        model = await provision_langchain_model(
            system_prompt,
            config.get("configurable", {}).get("answer_model"),
            "tools",
            max_tokens=2000,
            structured=dict(type="json"),
        )
        ai_message = await model.ainvoke(system_prompt)
        cleaned = clean_thinking_content(extract_text_content(ai_message.content))
        finding = parser.parse(cleaned)

        # Merge the principle context into the finding for the synthesis step.
        return {
            "findings": [
                {
                    "statement": principle.statement,
                    "rationale": principle.rationale,
                    "source_citations": principle.source_citations,
                    "verdict": finding.verdict,
                    "summary": finding.summary,
                    "evidence": finding.evidence,
                    "recommendation": finding.recommendation,
                }
            ]
        }
    except OpenNotebookError:
        raise
    except Exception as e:
        error_class, user_message = classify_error(e)
        raise error_class(user_message) from e


async def synthesize_report(state: ReviewState, config: RunnableConfig) -> dict:
    try:
        payload = {
            "theme": state["theme"],
            "repo_path": state["repo_path"],
            "findings": state.get("findings", []),
        }
        system_prompt = Prompter(prompt_template="repo_review/synthesize").render(  # type: ignore[arg-type]
            data=payload  # type: ignore[arg-type]
        )
        model = await provision_langchain_model(
            system_prompt,
            config.get("configurable", {}).get("final_answer_model"),
            "tools",
            max_tokens=4000,
        )
        ai_message = await model.ainvoke(system_prompt)
        report = clean_thinking_content(extract_text_content(ai_message.content))
        return {"report": report}
    except OpenNotebookError:
        raise
    except Exception as e:
        error_class, user_message = classify_error(e)
        raise error_class(user_message) from e


review_state = StateGraph(ReviewState)
review_state.add_node("distill", distill_guidance)
review_state.add_node("probe_principle", probe_principle)
review_state.add_node("synthesize_report", synthesize_report)
review_state.add_edge(START, "distill")
review_state.add_conditional_edges(
    "distill", trigger_probes, ["probe_principle", "synthesize_report"]
)
review_state.add_edge("probe_principle", "synthesize_report")
review_state.add_edge("synthesize_report", END)

graph = review_state.compile()
