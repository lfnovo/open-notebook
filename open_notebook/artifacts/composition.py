"""Section retrieval, grounded composition and citation verification.

One section at a time: run the planner's queries through vector search, keep
the best in-notebook excerpts, write the section from THOSE excerpts only, then
verify every citation against the excerpts actually passed to the model.

Citations carry the DOCUMENT reference number (``[source:2]``), never a record
id: the number is assigned once per document (see ``outline.SourceRef``) and is
shown both next to each excerpt and in the section's citable-reference list.
A citation that does not resolve to an excerpt actually passed to the model is
REMOVED from the text and reported - never silently trusted.
``render_citations`` then renders the resolved tokens as the plain ``[2]`` that
the numbered reference list appended at the end of the document matches.

The search callable is injected and awaited, so the whole layer is unit-tested
without a database or a network.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional, Sequence

from loguru import logger

from open_notebook.artifacts.outline import (
    DIAGRAM_RULES,
    SECTION_PROMPT,
    Complete,
    Section,
    SourceRef,
    instructions_block,
    kind_label,
    language_name,
    plan_outline,
    section_rules,
)
from open_notebook.domain.notebook import vector_search

#: One search call: query, hit limit, minimum similarity -> normalised hits.
Search = Callable[[str, int, float], Awaitable[list[dict[str, Any]]]]

#: ``[source:N]`` citations, by number or by full record id.
CITATION_RE = re.compile(r"\[source:([^\]\s]+)\]")

#: A resolved numeric citation, rendered as ``[N]`` in the final document.
CITATION_NUMBER_RE = re.compile(r"\[source:(\d+)\]")

#: A citation as it appears once rendered, used to collect what was cited.
RENDERED_CITATION_RE = re.compile(r"\[(\d+)\]")

#: Text appended to an excerpt cut to ``max_chars_per_chunk``.
TRUNCATION_MARK = " [truncated]"

#: A planned section we must drop: the reference list is appended by the command.
_BIBLIOGRAPHY_TITLE_RE = re.compile(
    r"^\s*(sources|references|bibliography)\s*$", re.IGNORECASE
)

_NO_CHUNKS_PLACEHOLDER = "(no excerpt retrieved)"


@dataclass
class Chunk:
    """One retrieved excerpt, ready to be pasted into a section prompt.

    Attributes:
        source_id: Source record id the excerpt comes from.
        title: Source title, used as a readable citation label.
        text: Excerpt text.
        similarity: Vector similarity reported by the search.
    """

    source_id: str
    title: str
    text: str
    similarity: float = 0.0


@dataclass
class RetrievalConfig:
    """Tuning knobs for the retrieval layer.

    These defaults ARE the app's behaviour: ``generate_artifact`` builds this
    config and overrides only ``outline_max_sections``, and no ``config.yaml``
    ships with the repository. They are sized for a LONG document - one section
    may hold tens of thousands of characters, i.e. a book chapter, not a slide.
    """

    enabled: bool = True
    outline_max_sections: int = 5
    chunks_per_query: int = 10
    max_chunks_per_section: int = 30
    max_chunks_per_source: int = 4
    max_chars_per_chunk: int = 2000
    max_chars_per_section: int = 40000
    min_score: float = 0.2
    verify_citations: bool = True


@dataclass
class CompositionConfig:
    """Tuning knobs for the writing stage.

    Attributes:
        language: Language the document body is written in.
        instructions: Optional user brief passed to every prompt.
        allow_diagrams: Ask the model for ```mermaid``` fences per section.
        model_id: Optional explicit Model record id.
        max_section_attempts: Calls per section; the retry halves the material.
        variant: Sub-variant of the kind (``document``/``illustrated`` for a
            report, ``presenter``/``detailed`` for a deck); ``None`` uses the
            kind's default.
    """

    language: str = "en"
    instructions: str = ""
    allow_diagrams: bool = False
    model_id: Optional[str] = None
    max_section_attempts: int = 2
    variant: Optional[str] = None


@dataclass
class SectionOutcome:
    """What one section produced, for the run report.

    Attributes:
        section: The planned section.
        chunks: Excerpts the section was written from.
        text: Verified section Markdown (empty when the model gave nothing).
        unknown_citations: Citation tokens dropped during verification.
    """

    section: Section
    chunks: list[Chunk] = field(default_factory=list)
    text: str = ""
    unknown_citations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the outcome for the run report.

        Returns:
            A JSON-serializable summary of the section.
        """
        return {
            "title": self.section.title,
            "thesis": self.section.thesis,
            "queries": list(self.section.queries),
            "chunks": [
                {
                    "source_id": chunk.source_id,
                    "chars": len(chunk.text),
                    "similarity": chunk.similarity,
                }
                for chunk in self.chunks
            ],
        }


def config_from_dict(raw: Optional[dict[str, Any]]) -> RetrievalConfig:
    """Build a RetrievalConfig from a plain mapping.

    Args:
        raw: Mapping with any subset of the RetrievalConfig fields.

    Returns:
        The retrieval configuration, missing keys taken from the defaults.
    """
    raw = raw or {}
    defaults = RetrievalConfig()
    return RetrievalConfig(
        enabled=bool(raw.get("enabled", defaults.enabled)),
        outline_max_sections=int(
            raw.get("outline_max_sections", defaults.outline_max_sections)
        ),
        chunks_per_query=int(raw.get("chunks_per_query", defaults.chunks_per_query)),
        max_chunks_per_section=int(
            raw.get("max_chunks_per_section", defaults.max_chunks_per_section)
        ),
        max_chunks_per_source=int(
            raw.get("max_chunks_per_source", defaults.max_chunks_per_source)
        ),
        max_chars_per_chunk=int(
            raw.get("max_chars_per_chunk", defaults.max_chars_per_chunk)
        ),
        max_chars_per_section=int(
            raw.get("max_chars_per_section", defaults.max_chars_per_section)
        ),
        min_score=float(raw.get("min_score", defaults.min_score)),
        verify_citations=bool(raw.get("verify_citations", defaults.verify_citations)),
    )


def normalize_hit(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize one ``vector_search()`` row to the internal hit shape.

    ``fn::vector_search`` returns ``{id, parent_id, title, similarity,
    matches}`` where ``matches`` is the flattened list of matched chunk texts;
    the retrieval layer works on ``{source_id, title, similarity, text}``.

    Args:
        row: Raw row from ``vector_search()``.

    Returns:
        The normalised hit.
    """
    matches = row.get("matches") or []
    if isinstance(matches, str):
        matches = [matches]
    text = "\n".join(str(match) for match in matches if isinstance(match, str))
    return {
        "source_id": str(row.get("parent_id") or row.get("source_id") or ""),
        "title": str(row.get("title") or ""),
        "similarity": row.get("similarity"),
        "text": text,
    }


def make_notebook_search(notebook_id: str) -> Search:
    """Build the section search callable for one notebook.

    Uses the domain's ``vector_search()`` scoped to the notebook, so results
    are limited server-side instead of being filtered client-side out of a
    global result set.

    Args:
        notebook_id: Notebook record id to scope the search to.

    Returns:
        An async callable ``(query, limit, min_score) -> hits``.
    """

    async def search(query: str, limit: int, min_score: float) -> list[dict[str, Any]]:
        rows = await vector_search(
            query,
            limit,
            source=True,
            note=False,
            minimum_score=min_score,
            notebook_ids=[notebook_id],
        )
        return [normalize_hit(row) for row in rows or []]

    return search


def short_id(source_id: str) -> str:
    """Drop the ``source:`` prefix so citations stay readable.

    Args:
        source_id: Full record id.

    Returns:
        The id without its table prefix.
    """
    sid = (source_id or "").strip()
    return sid.split(":", 1)[1] if sid.startswith("source:") else sid


def _similarity(hit: dict[str, Any]) -> float:
    """Read a hit's similarity, tolerating junk values.

    Args:
        hit: Normalised hit.

    Returns:
        The similarity as a float, or ``0.0`` when missing or unparsable.
    """
    try:
        return float(hit.get("similarity") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def select_chunks(
    hits: Sequence[dict[str, Any]],
    allowed_source_ids: Sequence[str],
    cfg: RetrievalConfig,
) -> list[Chunk]:
    """Filter hits to the notebook, dedupe, truncate and cap the budget.

    Excerpts are taken in two passes. The first honours
    ``max_chunks_per_source``, so one document cannot fill the whole budget
    (the failure this guards against: eight near-identical excerpts from a
    single source, every other source starved). The second fills whatever
    budget the cap left unused, best hits first.

    Args:
        hits: Normalised hits from one or more queries, best first.
        allowed_source_ids: Source ids belonging to the notebook.
        cfg: Retrieval configuration.

    Returns:
        The excerpts kept for one section, best first.
    """
    allowed = {sid for sid in allowed_source_ids if sid}
    prepared: list[tuple[str, str, str, float]] = []
    seen: set[tuple[str, str]] = set()

    for hit in hits:
        source_id = str(hit.get("source_id") or "")
        if allowed and source_id not in allowed:
            continue
        text = str(hit.get("text") or "").strip()
        if not text:
            continue
        if len(text) > cfg.max_chars_per_chunk:
            text = text[: cfg.max_chars_per_chunk] + TRUNCATION_MARK
        key = (source_id, text[:100])
        if key in seen:
            continue
        seen.add(key)
        prepared.append(
            (source_id, str(hit.get("title") or ""), text, _similarity(hit))
        )

    selected: list[Chunk] = []
    taken: set[int] = set()
    per_source: dict[str, int] = {}
    total_chars = 0

    def fill(cap: Optional[int]) -> None:
        nonlocal total_chars
        for index, (source_id, title, text, similarity) in enumerate(prepared):
            if index in taken:
                continue
            if len(selected) >= cfg.max_chunks_per_section:
                return
            if total_chars + len(text) > cfg.max_chars_per_section and selected:
                return
            if cap is not None and per_source.get(source_id, 0) >= cap:
                continue
            selected.append(
                Chunk(
                    source_id=source_id,
                    title=title,
                    text=text,
                    similarity=similarity,
                )
            )
            taken.add(index)
            per_source[source_id] = per_source.get(source_id, 0) + 1
            total_chars += len(text)

    cap = cfg.max_chunks_per_source if cfg.max_chunks_per_source > 0 else None
    if cap is not None:
        fill(cap)
    fill(None)
    return selected


async def retrieve_for_section(
    search: Search,
    section: Section,
    allowed_source_ids: Sequence[str],
    cfg: RetrievalConfig,
) -> list[Chunk]:
    """Run the section's queries and keep the best in-notebook excerpts.

    Args:
        search: Injected search callable.
        section: Planned section.
        allowed_source_ids: Source ids belonging to the notebook.
        cfg: Retrieval configuration.

    Returns:
        The excerpts for the section; a failed query is logged and skipped.
    """
    hits: list[dict[str, Any]] = []
    for query in section.queries:
        try:
            hits.extend(await search(query, cfg.chunks_per_query, cfg.min_score))
        except Exception as exc:
            logger.warning(f"Search failed for {query!r}: {exc}")
    hits.sort(key=_similarity, reverse=True)
    chunks = select_chunks(hits, allowed_source_ids, cfg)
    logger.info(f"Section {section.title!r}: {len(chunks)} excerpt(s)")
    return chunks


def chunks_block(
    chunks: Sequence[Chunk], numbers: Optional[dict[str, int]] = None
) -> str:
    """Render excerpts with a SHORT citation label the model can copy.

    Args:
        chunks: Excerpts for one section.
        numbers: Mapping of source record id -> reference number. When a source
            is missing from it the excerpt's position in this section is used.

    Returns:
        The excerpt block for the prompt, numbered from 1.
    """
    if not chunks:
        return _NO_CHUNKS_PLACEHOLDER
    mapping = numbers or {}
    parts = []
    for index, chunk in enumerate(chunks, start=1):
        title = chunk.title or short_id(chunk.source_id)
        number = mapping.get(chunk.source_id, index)
        parts.append(f"[source:{number}] (source: {title})\n{chunk.text}")
    return "\n\n".join(parts)


def references_block(
    chunks: Sequence[Chunk], numbers: Optional[dict[str, int]] = None
) -> str:
    """List the references the model may cite in this section.

    Only the sources actually excerpted for the section are listed: a number
    the model can see but cannot read would invite ungrounded citations.

    Args:
        chunks: Excerpts for one section.
        numbers: Mapping of source record id -> reference number.

    Returns:
        One ``[N] Title`` line per distinct source, or a placeholder.
    """
    mapping = numbers or {}
    lines: list[str] = []
    seen: set[int] = set()
    for index, chunk in enumerate(chunks, start=1):
        number = mapping.get(chunk.source_id, index)
        if number in seen:
            continue
        seen.add(number)
        title = chunk.title or short_id(chunk.source_id)
        lines.append(f"[{number}] {title}")
    return "\n".join(lines) if lines else "- (none)"


def build_section_prompt(
    section: Section,
    chunks: Sequence[Chunk],
    kind: str,
    language: str,
    instructions: str = "",
    allow_diagrams: bool = False,
    numbers: Optional[dict[str, int]] = None,
    variant: Optional[str] = None,
) -> str:
    """Assemble the prompt for one section.

    Args:
        section: Planned section.
        chunks: Excerpts retrieved for the section.
        kind: Artifact kind.
        language: Language the section is written in (code or name).
        instructions: Optional user brief.
        allow_diagrams: Ask for a ```mermaid``` fence when the section fits.
        numbers: Mapping of source record id -> document reference number.
        variant: Sub-variant (report: ``document``/``illustrated``; deck:
            ``presenter``/``detailed``). ``None`` selects the kind's default.

    Returns:
        The complete section prompt.
    """
    return SECTION_PROMPT.format(
        kind_label=kind_label(kind),
        title=section.title,
        thesis=section.thesis or "(none)",
        instructions_block=instructions_block(instructions),
        references_block=references_block(chunks, numbers),
        chunks_block=chunks_block(chunks, numbers),
        language=language_name(language),
        rules=section_rules(kind, variant),
        diagrams=DIAGRAM_RULES if allow_diagrams else "",
    )


async def generate_section(
    complete: Complete,
    section: Section,
    chunks: Sequence[Chunk],
    kind: str,
    cfg: CompositionConfig,
    numbers: Optional[dict[str, int]] = None,
) -> str:
    """Write one section; a failure degrades instead of killing the run.

    Args:
        complete: Injected model callable.
        section: Planned section.
        chunks: Excerpts the section is written from.
        kind: Artifact kind.
        cfg: Composition configuration.
        numbers: Mapping of source record id -> document reference number.

    Returns:
        The section Markdown, or an empty string when the call failed.
    """
    prompt = build_section_prompt(
        section,
        chunks,
        kind,
        cfg.language,
        cfg.instructions,
        cfg.allow_diagrams,
        numbers,
        cfg.variant,
    )
    try:
        return await complete(prompt)
    except Exception as exc:
        logger.warning(
            f"Section {section.title!r} call failed ({type(exc).__name__}: {exc})"
        )
        return ""


async def compose_section(
    complete: Complete,
    section: Section,
    chunks: list[Chunk],
    kind: str,
    cfg: CompositionConfig,
    numbers: Optional[dict[str, int]] = None,
) -> tuple[str, list[Chunk]]:
    """Write one section, retrying with half the material when it comes back empty.

    A reasoning model can burn its whole token budget thinking or stall past
    the read timeout (measured: one section at 192 s while its siblings took
    ~5 s), so an empty reply is retried with half the excerpts - the retry is
    genuinely lighter. Returns the excerpts that were actually used.

    Args:
        complete: Injected model callable.
        section: Planned section.
        chunks: Excerpts retrieved for the section.
        kind: Artifact kind.
        cfg: Composition configuration.
        numbers: Mapping of source record id -> document reference number.

    Returns:
        ``(section_markdown, chunks_used)``; the Markdown is empty when every
        attempt failed.
    """
    text = await generate_section(complete, section, chunks, kind, cfg, numbers)
    attempts = max(cfg.max_section_attempts, 1)
    if text.strip() or attempts < 2 or len(chunks) <= 2:
        return text, chunks

    halves = chunks[: max(len(chunks) // 2, 1)]
    logger.warning(
        f"Section {section.title!r} produced nothing with {len(chunks)} excerpt(s)"
        f" - retrying with {len(halves)}"
    )
    text = await generate_section(complete, section, halves, kind, cfg, numbers)
    return (text, halves) if text.strip() else (text, chunks)


def citation_numbers(
    chunks: Sequence[Chunk], numbers: Optional[dict[str, int]] = None
) -> dict[str, int]:
    """Resolve every excerpt's source to the number used in citations.

    Args:
        chunks: Excerpts passed to the model, in prompt order.
        numbers: Mapping of source record id -> document reference number. When
            a source is missing from it, the excerpt's position is used.

    Returns:
        Mapping of source record id -> citation number.
    """
    mapping = numbers or {}
    return {
        chunk.source_id: mapping.get(chunk.source_id, index)
        for index, chunk in enumerate(chunks, start=1)
        if chunk.source_id
    }


def verify_citations(
    markdown: str,
    chunks: Sequence[Chunk],
    numbers: Optional[dict[str, int]] = None,
) -> tuple[str, list[str]]:
    """Keep only citations that point at an excerpt actually provided.

    Args:
        markdown: Section Markdown as returned by the model.
        chunks: Excerpts passed to the model, in prompt order.
        numbers: Mapping of source record id -> document reference number.

    Returns:
        ``(cleaned_markdown, unknown_tokens)`` where ``unknown_tokens`` holds
        the citation tokens that were removed.
    """
    resolved = citation_numbers(chunks, numbers)
    allowed = set(resolved.values())
    by_label = {short_id(source_id): number for source_id, number in resolved.items()}
    unknown: list[str] = []

    def replace(match: re.Match[str]) -> str:
        token = match.group(1).strip()
        if token.isdigit():
            number = int(token)
            if number in allowed:
                return f"[source:{number}]"
            unknown.append(token)
            return ""
        short = short_id(token)
        if short in by_label:
            return f"[source:{by_label[short]}]"
        unknown.append(short)
        return ""

    cleaned = CITATION_RE.sub(replace, markdown)
    if unknown:
        logger.warning(
            f"Removed {len(unknown)} citation(s) pointing outside the excerpts:"
            f" {sorted(set(unknown))}"
        )
    return cleaned, sorted(set(unknown))


def render_citations(markdown: str) -> str:
    """Render resolved citation tokens as plain numbers.

    ``[source:3]`` becomes ``[3]``, matching the numbered reference list the
    command appends. Non-numeric tokens are left alone.

    Args:
        markdown: Section Markdown whose citations resolved.

    Returns:
        The Markdown with numeric citation tokens rendered.
    """
    return CITATION_NUMBER_RE.sub(r"[\1]", markdown)


def assemble_document(title: str, sections_markdown: Sequence[str]) -> str:
    """Concatenate the per-section Markdown into one document.

    Args:
        title: Document title.
        sections_markdown: Section bodies, in order.

    Returns:
        The full Markdown document.
    """
    body = "\n\n".join(s.strip() for s in sections_markdown if s and s.strip())
    header = f"# {title}\n" if title else ""
    return f"{header}\n{body}\n".lstrip("\n")


async def build_document(
    complete: Complete,
    search: Search,
    sources: Sequence[SourceRef],
    title: str,
    kind: str,
    cfg: RetrievalConfig,
    composition: Optional[CompositionConfig] = None,
    sections: Optional[Sequence[Section]] = None,
) -> tuple[str, dict[str, Any]]:
    """Outline -> retrieve -> write -> verify -> assemble.

    Every notebook source is numbered once, up front: the same number labels the
    source's excerpts and its entry in the trailing reference list, so a citation
    keeps its meaning wherever it appears in the document. Sections the planner
    still devotes to a bibliography are dropped - that list is appended by the
    command, never written by the model.

    Args:
        complete: Injected model callable.
        search: Injected search callable.
        sources: Sources of the notebook, in reference order.
        title: Document title.
        kind: Artifact kind.
        cfg: Retrieval configuration.
        composition: Writing configuration; defaults are used when omitted.
        sections: Pre-planned sections; the outline is planned when omitted.

    Returns:
        ``(markdown_document, report)`` where the report carries the numbered
        references, every section, its excerpts and the dropped citations.
    """
    comp = composition or CompositionConfig()
    references = [
        {
            "number": number,
            "source_id": source.source_id,
            "title": source.title,
            "url": source.url,
        }
        for number, source in enumerate(sources, start=1)
    ]
    numbers = {
        source.source_id: number
        for number, source in enumerate(sources, start=1)
        if source.source_id
    }
    allowed_source_ids = [source.source_id for source in sources if source.source_id]

    planned = (
        list(sections)
        if sections
        else await plan_outline(
            [source.title for source in sources],
            title,
            kind,
            comp.instructions,
            cfg.outline_max_sections,
            model_id=comp.model_id,
            language=comp.language,
        )
    )
    planned = [
        section
        for section in planned
        if not _BIBLIOGRAPHY_TITLE_RE.match(section.title)
    ]

    outcomes: list[SectionOutcome] = []
    total = len(planned)
    for position, section in enumerate(planned, start=1):
        logger.info(f"Section {position}/{total}: {section.title}")
        chunks = await retrieve_for_section(search, section, allowed_source_ids, cfg)
        text, used = await compose_section(
            complete, section, chunks, kind, comp, numbers
        )
        outcome = SectionOutcome(section=section, chunks=used)
        if not text.strip():
            logger.warning(f"Section {section.title!r} produced no content - skipped")
        else:
            if cfg.verify_citations:
                text, unknown = verify_citations(text, used, numbers)
                outcome.unknown_citations = unknown
                text = render_citations(text)
            outcome.text = text
        outcomes.append(outcome)

    written = [outcome.text for outcome in outcomes if outcome.text.strip()]
    document = assemble_document(title, written)
    unknown_all = sorted(
        {token for outcome in outcomes for token in outcome.unknown_citations}
    )
    # What the body actually cites: the reference list must not grow entries
    # for sources that were retrieved for a section that then produced nothing.
    cited_numbers = sorted(
        {int(number) for number in RENDERED_CITATION_RE.findall(document)}
    )
    report: dict[str, Any] = {
        "mode": "retrieval",
        "references": references,
        "cited_numbers": cited_numbers,
        "sections": [outcome.to_dict() for outcome in outcomes],
        "sections_written": len(written),
        "unknown_citations": unknown_all,
        "chars": len(document),
    }
    return document, report
