"""Outline planning and the LLM bridge for the native artifact pipeline.

The pipeline never stuffs a whole notebook into one prompt. It plans first:
one LLM call returns a JSON list of sections, each with 1-3 concrete search
queries, and ``composition`` then retrieves and writes one section at a time
(Lost in the Middle, TACL 2023; Context Rot, Chroma 2025 - output quality
decays as the input grows and with topical distractors).

This module also owns ``complete_text()``, the single LLM call site for the
whole package: everything goes through ``provision_langchain_model()``, so the
model is chosen by the user's configuration (Manage -> Models) instead of a
hard-coded endpoint, and thinking tokens are stripped with the same helper the
graphs use.

Everything except ``complete_text()`` is pure Python, so the parsing layer is
unit-tested without touching the network.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional, Sequence

from loguru import logger

from open_notebook.ai.provision import provision_langchain_model
from open_notebook.utils.text_utils import (
    clean_thinking_content,
    extract_text_content,
)

#: One model call: prompt in, raw reply text out.
Complete = Callable[[str], Awaitable[str]]

#: Artifact kinds. ``deck`` is the slide presentation (the standalone pipeline
#: called it ``slides``; the stored record uses the spec's naming).
KINDS = ("report", "deck")

DEFAULT_MAX_SECTIONS = 5
DEFAULT_LANGUAGE = "en"

#: NotebookLM-style sub-variants, one pair per kind. The name states what the
#: deliverable IS, never how it is consumed: "interactive" was rejected because
#: in NotebookLM it means an embedded, playable Studio artifact, while our
#: text-with-figures report is simply an ILLUSTRATED document.
VARIANTS: dict[str, tuple[str, ...]] = {
    "report": ("document", "illustrated"),
    "deck": ("presenter", "detailed"),
}

#: Variant used when the request does not name one.
DEFAULT_VARIANTS: dict[str, str] = {
    "report": "document",
    "deck": "presenter",
}

#: Output-token budgets for the model calls.
#:
#: The provisioned model is built with a very small default budget (measured:
#: 850 tokens with an OpenRouter model), and a REASONING model spends that
#: whole budget inside its thinking block: the reply comes back with
#: ``finish_reason=length`` and EMPTY content, so the outline silently degrades
#: to the fallback skeleton and most sections are dropped. The app already
#: passes an explicit budget elsewhere for the same reason (``graphs/chat.py``
#: uses 8192), so the artifact calls do too.
#:
#: Measured again on a 6-section deck over 33 sources (2026-09-21): at 4096 the
#: reasoning model still returned an empty reply for 3 sections, and one of them
#: never recovered on the retry and was dropped from the document. At 8192 one
#: section came back TRUNCATED mid-sentence ("- A harness is the"). A section is
#: now allowed to be a book chapter, so the visible reply must have room to
#: exceed the thinking block by a wide margin: hence 16384.
DEFAULT_COMPLETION_MAX_TOKENS = 16384
DEFAULT_OUTLINE_MAX_TOKENS = 4096

#: Planner attempts. Measured: a reasoning model occasionally answers the
#: planning prompt with prose or an empty block instead of the JSON object, and
#: a single bad reply used to drop the whole document onto the generic
#: fallback skeleton (English, no relation to the sources) - so the planning
#: call is retried once before giving up.
DEFAULT_OUTLINE_ATTEMPTS = 2

#: ISO 639-1 code -> the language NAME a model reliably understands.
#: Measured: "Write in it" gets ignored, "Write in Italian" does not.
LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "it": "Italian",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
    "zh": "Chinese",
    "ja": "Japanese",
    "ru": "Russian",
    "pl": "Polish",
    "tr": "Turkish",
    "ca": "Catalan",
    "bn": "Bengali",
}

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)
_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*\n(.*?)\n```\s*$", re.DOTALL)


@dataclass
class Section:
    """One planned section of the document.

    Attributes:
        title: Short section title (max ~6 words).
        thesis: One-line claim the section must support.
        queries: 1-3 search keywords used to retrieve the section's material.
    """

    title: str
    thesis: str = ""
    queries: list[str] = field(default_factory=list)


@dataclass
class SourceRef:
    """One notebook source, numbered for citation in the final document.

    Attributes:
        source_id: Source record id.
        title: Human-readable source title, used as the citation label.
        url: Source URL; empty for sources that are not links (e.g. pasted text).
    """

    source_id: str
    title: str = ""
    url: str = ""


OUTLINE_PROMPT = """You are an editor planning a technical document.

TITLE: {title}
DOCUMENT TYPE: {kind_label}
SOURCES AVAILABLE IN THE NOTEBOOK:
{source_list}
{instructions_block}{language_block}
Plan the document in AT MOST {max_sections} sections.

MANDATORY RULES:
- Reply with a valid JSON object ONLY. No comments, no code fences.
- Exact format:
  {{"sections": [{{"title": "...", "thesis": "...", "queries": ["...", "..."]}}]}}
- "title": short (max 6 words). "thesis": one line (the claim of the section).
- "queries": 1 to 3 search strings (concrete keywords that appear in the
  sources, NOT questions) used to retrieve that section's material.
- If two sections would use the same material, merge them.
- Cover the topic completely but without repetition.
- Prefer a FEW, BROAD chapters: each section is a chapter of a book, not a
  topic heading. Merge two thin sections into one rather than splitting.
- Never plan a "Sources", "References" or "Bibliography" section: that list is
  appended automatically, from the sources actually cited.
"""

SECTION_RULES_DECK = """- Bullets first: one idea per bullet, short (max 25 words).
- Use as many bullets as the MATERIAL supports (4 to 12). Never pad to reach a
  number and never compress to fit one.
- Use a short paragraph instead of a list when a list would distort the
  content: a wall of fragments is worse than one clear paragraph.
- The shape serves the material, not the other way around."""

#: A "detailed" deck adds prose to each bullet; the presenter rules still apply,
#: so they are appended instead of duplicated.
SECTION_RULES_DECK_DETAILED = (
    "- Be thorough: write full sentences under every bullet, not fragments, so a\n"
    "  slide reads as a self-contained explanation on its own (2 to 4 full\n"
    "  sentences per bullet where the material supports it).\n"
    "- A bullet with no sentence next to it is a presenter cue, not a detailed\n"
    "  slide: this variant exists to be read, not only spoken from.\n"
    + SECTION_RULES_DECK
)

SECTION_RULES_REPORT = """- Write PROSE in paragraphs. Use a bullet list only when the material really
  is a list: a chapter made of bullets is not a book.
- This section is a CHAPTER: aim for 700-1200 words, developed in several
  paragraphs around the concrete details of the MATERIAL.
- Depth over brevity: do not cut the reasoning short, and never pad or repeat
  yourself to reach the length."""

DIAGRAM_RULES = """- If the section describes a process, an architecture, a flow or a
  structured comparison, add ONE ```mermaid block with a valid diagram
  (flowchart/graph), AFTER the section text.
- Max 8 nodes, short labels (1-3 words); use only information from the MATERIAL.
- ALWAYS write a text sentence before the diagram: the slide layout needs it.
- Do not generate diagrams for lists of facts, for the summary or for the
  final "Sources" section."""

SECTION_PROMPT = """Write ONE section of {kind_label}.

SECTION TITLE: {title}
THESIS: {thesis}
{instructions_block}
CITABLE REFERENCES (the only sources you may cite in this section):
{references_block}

MATERIAL (excerpts retrieved from the sources; every excerpt is preceded by the
reference number of the source it comes from):
{chunks_block}

MANDATORY RULES:
- Use the MATERIAL only. Do not invent facts, numbers or names.
- Every time you state something specific add the citation [source:N] using the
  reference number that precedes the excerpt it comes from (e.g. [source:1]).
- Never cite a number that is not listed under CITABLE REFERENCES.
- Never write a "Sources", "References" or "Bibliography" section: it is
  appended automatically, with the source titles and links.
- Write in {language}.
- Start the answer with "## {title}" and do not repeat the title elsewhere.
{rules}
{diagrams}
"""

FALLBACK_SECTION_TITLES = (
    "Overview",
    "Key points",
    "Details",
    "Limits and uncertainties",
    "Sources",
)


def normalize_kind(kind: Optional[str]) -> str:
    """Coerce a user-supplied kind to one of ``KINDS``.

    Args:
        kind: Requested kind, possibly ``None`` or the legacy ``slides``.

    Returns:
        ``"deck"`` for slide-style artifacts, ``"report"`` otherwise.
    """
    return "deck" if (kind or "").strip().lower() in ("deck", "slides") else "report"


def kind_label(kind: str) -> str:
    """Human label used inside the prompts.

    Args:
        kind: Artifact kind.

    Returns:
        ``"a slide presentation"`` for a deck, ``"a report"`` otherwise.
    """
    return "a slide presentation" if normalize_kind(kind) == "deck" else "a report"


def normalize_variant(kind: Optional[str], variant: Optional[str]) -> str:
    """Coerce a requested variant to one valid for the artifact kind.

    Args:
        kind: Requested kind (``report``/``deck``, legacy ``slides`` allowed).
        variant: Requested variant; ``None`` or empty selects the default.

    Returns:
        The variant name, one of ``VARIANTS[kind]``.

    Raises:
        ValueError: If the variant belongs to the other kind (e.g. a report
            asked for the deck's ``presenter`` variant).
    """
    normalized_kind = normalize_kind(kind)
    allowed = VARIANTS[normalized_kind]
    requested = (variant or "").strip().lower()
    if not requested:
        return DEFAULT_VARIANTS[normalized_kind]
    if requested not in allowed:
        raise ValueError(
            f"variant {variant!r} is not valid for a {normalized_kind}; "
            f"choose one of: {', '.join(allowed)}"
        )
    return requested


def variant_allows_diagrams(kind: Optional[str], variant: Optional[str]) -> bool:
    """Whether this kind+variant may include ```mermaid``` diagrams.

    A deck is inherently visual, so both of its variants keep diagrams; a
    report only gets them in the ``illustrated`` variant, because the plain
    document must stay text only.

    Args:
        kind: Artifact kind.
        variant: Requested variant, or ``None`` for the kind's default.

    Returns:
        ``True`` when diagrams are allowed.
    """
    normalized_kind = normalize_kind(kind)
    normalized_variant = normalize_variant(normalized_kind, variant)
    if normalized_kind == "deck":
        return True
    return normalized_variant == "illustrated"


def section_rules(kind: Optional[str], variant: Optional[str] = None) -> str:
    """Rules block for one section, chosen by kind and variant.

    Args:
        kind: Artifact kind.
        variant: Requested variant, or ``None`` for the kind's default.

    Returns:
        The rules text injected into the section prompt.
    """
    normalized_kind = normalize_kind(kind)
    if normalized_kind == "deck":
        detailed = normalize_variant(normalized_kind, variant) == "detailed"
        return SECTION_RULES_DECK_DETAILED if detailed else SECTION_RULES_DECK
    return SECTION_RULES_REPORT


def instructions_block(instructions: str) -> str:
    """Render the optional user brief as a prompt fragment.

    Args:
        instructions: Free-text brief from the user, may be empty.

    Returns:
        The brief as an indented prompt block, or an empty string.
    """
    text = (instructions or "").strip()
    if not text:
        return ""
    return (
        f"\nUSER INSTRUCTIONS (they take priority on scope, focus and tone):\n{text}\n"
    )


def language_name(value: str) -> str:
    """Translate a language code to the name used inside the prompts.

    A model asked to "write in it" regularly answers in English, while "write
    in Italian" is followed reliably; the API passes whatever the client sent,
    which is normally an ISO 639-1 code.

    Args:
        value: Language code (``it``) or an already human-readable name
            (``Italian``).

    Returns:
        The language name, or the input unchanged when it is not a known code.
    """
    text = (value or "").strip()
    return LANGUAGE_NAMES.get(text.lower(), text)


def language_block(language: str) -> str:
    """Render the outline language instruction.

    Args:
        language: Language code or name.

    Returns:
        The instruction as a prompt block, or an empty string when unset.
    """
    name = language_name(language)
    if not name:
        return ""
    return f"\nWrite the section titles in {name}.\n"


def strip_code_fences(text: str) -> str:
    """Remove a wrapping ```...``` block if the model added one.

    Args:
        text: Raw model reply.

    Returns:
        The reply without an enclosing code fence.
    """
    stripped = (text or "").strip()
    fence = _FENCE_RE.match(stripped)
    return fence.group(1).strip() if fence else stripped


async def complete_text(
    prompt: str,
    model_id: Optional[str] = None,
    default_type: str = "chat",
    max_tokens: int = DEFAULT_COMPLETION_MAX_TOKENS,
) -> str:
    """Run one prompt through the provisioned language model.

    Args:
        prompt: Full prompt to send.
        model_id: Optional explicit Model record id; when omitted the default
            model for ``default_type`` is used.
        default_type: Default-model type to fall back on (``chat``).
        max_tokens: Output-token budget. Passed explicitly because the
            provisioned default is far too small for a reasoning model, which
            would return an empty reply after thinking (see
            ``DEFAULT_COMPLETION_MAX_TOKENS``).

    Returns:
        The reply text, with thinking blocks and code fences removed.

    Raises:
        ConfigurationError: If no usable language model is configured.
    """
    model = await provision_langchain_model(
        prompt, model_id, default_type, max_tokens=max_tokens
    )
    response = await model.ainvoke(prompt)
    content = extract_text_content(response.content)
    return strip_code_fences(clean_thinking_content(content))


def build_outline_prompt(
    source_titles: Sequence[str],
    title: str,
    kind: str,
    instructions: str = "",
    max_sections: int = DEFAULT_MAX_SECTIONS,
    language: str = "",
) -> str:
    """Assemble the single planning prompt.

    Args:
        source_titles: Titles of the sources in the notebook.
        title: Document title (may be empty).
        kind: Artifact kind.
        instructions: Optional user brief.
        max_sections: Maximum number of sections the planner may produce.
        language: Language code or name for the section titles.

    Returns:
        The complete outline prompt.
    """
    source_list = "\n".join(f"- {t}" for t in source_titles if t) or "- (no title)"
    return OUTLINE_PROMPT.format(
        title=title or "(to be decided)",
        kind_label=kind_label(kind),
        source_list=source_list,
        instructions_block=instructions_block(instructions),
        language_block=language_block(language),
        max_sections=max_sections,
    )


def parse_outline(text: str, max_sections: int) -> list[Section]:
    """Parse the planner reply into sections.

    Args:
        text: Raw planner reply (JSON object, possibly fenced).
        max_sections: Hard cap on the number of sections kept.

    Returns:
        The planned sections; a section with no query falls back to its title.

    Raises:
        ValueError: If the reply has no JSON object, is not valid JSON, has no
            usable ``sections`` list, or yields no section with a title.
    """
    raw = strip_code_fences(text)
    match = _JSON_OBJECT_RE.search(raw)
    if not match:
        raise ValueError("outline reply has no JSON object")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError(f"outline reply is not valid JSON: {exc}") from exc
    items = data.get("sections") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        raise ValueError("outline reply has no 'sections' list")

    sections: list[Section] = []
    for item in items[:max_sections]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        queries = [
            str(q).strip() for q in (item.get("queries") or []) if str(q).strip()
        ]
        sections.append(
            Section(
                title=title,
                thesis=str(item.get("thesis") or "").strip(),
                queries=queries or [title],
            )
        )
    if not sections:
        raise ValueError("outline produced no usable section")
    return sections


def fallback_outline(
    title: str, max_sections: int = DEFAULT_MAX_SECTIONS
) -> list[Section]:
    """Deterministic outline used when the planner reply is unusable.

    The standalone pipeline fell back to a single whole-notebook call when the
    planner failed; that mode is deliberately not ported (it is what the
    retrieval design exists to avoid), so an unusable reply degrades to a
    generic document skeleton instead of aborting the run.

    Args:
        title: Document title, used as an additional search query.
        max_sections: Hard cap on the number of sections produced.

    Returns:
        A fixed skeleton outline (Overview, Key points, Details, ...).
    """
    sections: list[Section] = []
    for section_title in FALLBACK_SECTION_TITLES[:max_sections]:
        queries = [title, section_title] if title.strip() else [section_title]
        sections.append(Section(title=section_title, queries=queries))
    return sections


async def plan_outline(
    source_titles: Sequence[str],
    title: str,
    kind: str,
    instructions: str = "",
    max_sections: int = DEFAULT_MAX_SECTIONS,
    model_id: Optional[str] = None,
    language: str = "",
    attempts: int = DEFAULT_OUTLINE_ATTEMPTS,
) -> list[Section]:
    """Plan the document with one LLM call, retried once on a bad reply.

    Args:
        source_titles: Titles of the sources in the notebook.
        title: Document title (may be empty).
        kind: Artifact kind.
        instructions: Optional user brief.
        max_sections: Maximum number of sections.
        model_id: Optional explicit Model record id.
        language: Language code or name for the section titles.
        attempts: How many times to ask before falling back.

    Returns:
        The planned sections, or ``fallback_outline()`` when every reply is
        unusable.
    """
    prompt = build_outline_prompt(
        source_titles, title, kind, instructions, max_sections, language
    )
    last_error = ""
    for attempt in range(1, max(attempts, 1) + 1):
        reply: Any = await complete_text(
            prompt, model_id=model_id, max_tokens=DEFAULT_OUTLINE_MAX_TOKENS
        )
        try:
            sections = parse_outline(reply, max_sections)
        except ValueError as exc:
            last_error = str(exc)
            logger.warning(f"Outline attempt {attempt}/{attempts} unusable ({exc})")
            continue
        logger.info(f"Outline planned: {len(sections)} section(s)")
        return sections

    logger.warning(
        f"Outline unusable after {attempts} attempt(s) ({last_error}); "
        "using the default outline"
    )
    return fallback_outline(title, max_sections)
