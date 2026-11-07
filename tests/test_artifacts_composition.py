"""Unit tests for section retrieval, grounded composition and citations.

The model call and the vector search are injected, so no test here touches the
network, the database or an embedding model.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from open_notebook.artifacts import composition, outline


def make_hit(source_id="source:aaa", title="Source A", text="body", similarity=0.9):
    """Build one normalised search hit."""
    return {
        "source_id": source_id,
        "title": title,
        "similarity": similarity,
        "text": text,
    }


class FakeSearch:
    """Search callable returning canned hits and recording the queries."""

    def __init__(self, hits):
        self.hits = list(hits)
        self.calls: list[tuple[str, int, float]] = []

    async def __call__(self, query, limit, min_score):
        self.calls.append((query, limit, min_score))
        return list(self.hits)


class FakeComplete:
    """Model callable answering canned replies in order, recording prompts."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts: list[str] = []

    async def __call__(self, prompt):
        self.prompts.append(prompt)
        return self.replies.pop(0) if self.replies else ""


def make_search(hits):
    """Build an injected search callable returning the given hits."""
    return FakeSearch(hits)


def make_complete(replies):
    """Build an injected model callable answering the given replies in order."""
    return FakeComplete(replies)


class TestSelectChunks:
    def test_hits_outside_the_notebook_are_dropped(self):
        chunks = composition.select_chunks(
            [make_hit(), make_hit(source_id="source:other")],
            ["source:aaa"],
            composition.RetrievalConfig(),
        )
        assert [c.source_id for c in chunks] == ["source:aaa"]

    def test_empty_allowed_list_keeps_every_hit(self):
        chunks = composition.select_chunks(
            [make_hit(), make_hit(source_id="source:other")],
            [],
            composition.RetrievalConfig(),
        )
        assert len(chunks) == 2

    def test_empty_text_is_dropped(self):
        chunks = composition.select_chunks(
            [make_hit(text="   "), make_hit(text="real")],
            ["source:aaa"],
            composition.RetrievalConfig(),
        )
        assert [c.text for c in chunks] == ["real"]

    def test_duplicates_are_dropped(self):
        chunks = composition.select_chunks(
            [make_hit(), make_hit()], ["source:aaa"], composition.RetrievalConfig()
        )
        assert len(chunks) == 1

    def test_long_excerpts_are_truncated(self):
        cfg = composition.RetrievalConfig(max_chars_per_chunk=5)
        chunks = composition.select_chunks([make_hit(text="abcdefghij")], [], cfg)
        assert chunks[0].text == "abcde" + composition.TRUNCATION_MARK

    def test_chunk_count_is_capped(self):
        cfg = composition.RetrievalConfig(max_chunks_per_section=2)
        hits = [make_hit(text=f"body {i}") for i in range(5)]
        assert len(composition.select_chunks(hits, [], cfg)) == 2

    def test_section_char_budget_is_respected(self):
        cfg = composition.RetrievalConfig(max_chars_per_section=20)
        hits = [make_hit(text="aaaaaa"), make_hit(text="bbbbbbbb")]
        assert len(composition.select_chunks(hits, [], cfg)) == 2

    def test_section_char_budget_stops_the_section(self):
        cfg = composition.RetrievalConfig(max_chars_per_section=10)
        hits = [make_hit(text="aaaaaaa"), make_hit(text="bbbbbbb")]
        assert len(composition.select_chunks(hits, [], cfg)) == 1

    def test_unparsable_similarity_becomes_zero(self):
        hit = make_hit()
        hit["similarity"] = "not-a-number"
        chunks = composition.select_chunks([hit], [], composition.RetrievalConfig())
        assert chunks[0].similarity == 0.0

    def test_one_source_cannot_fill_the_whole_budget(self):
        hits = [make_hit(text=f"a{i}") for i in range(5)]
        hits.append(make_hit(source_id="source:bbb", title="B", text="b0"))
        hits.append(make_hit(source_id="source:ccc", title="C", text="c0"))
        cfg = composition.RetrievalConfig(
            max_chunks_per_section=4, max_chunks_per_source=2
        )
        chunks = composition.select_chunks(hits, [], cfg)
        assert len(chunks) == 4
        assert {c.source_id for c in chunks} == {
            "source:aaa",
            "source:bbb",
            "source:ccc",
        }

    def test_the_cap_is_lifted_when_it_would_starve_the_budget(self):
        cfg = composition.RetrievalConfig(
            max_chunks_per_section=4, max_chunks_per_source=2
        )
        hits = [make_hit(text=f"a{i}") for i in range(6)]
        assert len(composition.select_chunks(hits, [], cfg)) == 4


class TestNormalizeHit:
    def test_vector_search_row_is_mapped_to_the_internal_shape(self):
        row = {
            "id": "source_embedding:1",
            "parent_id": "source:aaa",
            "title": "Source A",
            "similarity": 0.77,
            "matches": ["first", "second"],
        }
        hit = composition.normalize_hit(row)
        assert hit == {
            "source_id": "source:aaa",
            "title": "Source A",
            "similarity": 0.77,
            "text": "first\nsecond",
        }

    def test_missing_matches_become_empty_text(self):
        assert composition.normalize_hit({"parent_id": "source:aaa"})["text"] == ""


class TestMakeNotebookSearch:
    @pytest.mark.asyncio
    async def test_search_is_scoped_to_the_notebook(self, monkeypatch):
        rows = [
            {
                "parent_id": "source:aaa",
                "title": "Source A",
                "similarity": 0.8,
                "matches": ["excerpt"],
            }
        ]
        mock_search = AsyncMock(return_value=rows)
        monkeypatch.setattr(composition, "vector_search", mock_search)

        search = composition.make_notebook_search("notebook:nb1")
        hits = await search("alpha", 6, 0.2)

        await_args = mock_search.await_args
        assert await_args is not None
        kwargs = await_args.kwargs
        assert kwargs["notebook_ids"] == ["notebook:nb1"]
        assert kwargs["source"] is True and kwargs["note"] is False
        assert kwargs["minimum_score"] == 0.2
        assert hits[0]["source_id"] == "source:aaa"
        assert hits[0]["text"] == "excerpt"


class TestRetrieveForSection:
    @pytest.mark.asyncio
    async def test_every_query_is_run_and_hits_are_filtered(self):
        section = outline.Section(title="One", queries=["alpha", "beta"])
        search = make_search([make_hit(), make_hit(source_id="source:other")])
        chunks = await composition.retrieve_for_section(
            search, section, ["source:aaa"], composition.RetrievalConfig()
        )
        assert [call[0] for call in search.calls] == ["alpha", "beta"]
        assert [c.source_id for c in chunks] == ["source:aaa"]

    @pytest.mark.asyncio
    async def test_a_failing_query_does_not_kill_the_section(self):
        async def flaky(query, limit, min_score):
            if query == "bad":
                raise RuntimeError("search down")
            return [make_hit()]

        section = outline.Section(title="One", queries=["bad", "good"])
        chunks = await composition.retrieve_for_section(
            flaky, section, ["source:aaa"], composition.RetrievalConfig()
        )
        assert len(chunks) == 1


class TestVerifyCitations:
    NUMBERS = {"source:aaa": 1, "source:bbb": 2}

    def test_numbers_of_excerpted_sources_are_kept(self):
        chunks = [
            composition.Chunk(source_id="source:aaa", title="A", text="a"),
            composition.Chunk(source_id="source:bbb", title="B", text="b"),
        ]
        cleaned, unknown = composition.verify_citations(
            "Fact [source:1] and other [source:2].", chunks, self.NUMBERS
        )
        assert cleaned == "Fact [source:1] and other [source:2]."
        assert unknown == []

    def test_unresolvable_citations_are_dropped(self):
        chunks = [composition.Chunk(source_id="source:aaa", title="A", text="a")]
        cleaned, unknown = composition.verify_citations(
            "Kept [source:1]. Gone [source:9]. Gone [source:zzz].",
            chunks,
            self.NUMBERS,
        )
        assert cleaned == "Kept [source:1]. Gone . Gone ."
        assert unknown == ["9", "zzz"]

    def test_a_record_id_is_rewritten_to_its_number(self):
        chunks = [composition.Chunk(source_id="source:bbb", title="B", text="b")]
        cleaned, unknown = composition.verify_citations(
            "[source:bbb] twice [source:bbb]", chunks, self.NUMBERS
        )
        assert cleaned == "[source:2] twice [source:2]"
        assert unknown == []

    def test_a_number_outside_the_chunk_list_is_dropped(self):
        chunks = [composition.Chunk(source_id="source:aaa", title="A", text="a")]
        cleaned, unknown = composition.verify_citations(
            "[source:2]", chunks, self.NUMBERS
        )
        assert cleaned == ""
        assert unknown == ["2"]

    def test_numbers_fall_back_to_the_excerpt_position(self):
        chunks = [composition.Chunk(source_id="source:aaa", title="A", text="a")]
        cleaned, unknown = composition.verify_citations("[source:1]", chunks)
        assert cleaned == "[source:1]"
        assert unknown == []

    def test_text_without_citations_is_untouched(self):
        cleaned, unknown = composition.verify_citations("plain text", [])
        assert cleaned == "plain text"
        assert unknown == []


class TestRenderCitations:
    def test_resolved_tokens_become_plain_numbers(self):
        rendered = composition.render_citations("Fact [source:2]. More [source:10].")
        assert rendered == "Fact [2]. More [10]."

    def test_unresolved_tokens_are_left_alone(self):
        assert composition.render_citations("[source:aaa]") == "[source:aaa]"


class TestReferencesBlock:
    def test_only_the_excerpted_sources_are_listed_once(self):
        chunks = [
            composition.Chunk(source_id="source:aaa", title="A", text="a"),
            composition.Chunk(source_id="source:bbb", title="B", text="b"),
            composition.Chunk(source_id="source:aaa", title="A", text="a again"),
        ]
        block = composition.references_block(chunks, {"source:aaa": 3, "source:bbb": 7})
        assert block == "[3] A\n[7] B"

    def test_without_chunks_the_block_is_a_placeholder(self):
        assert composition.references_block([], {}) == "- (none)"

    def test_the_number_and_title_reach_the_section_prompt(self):
        section = outline.Section(title="One", queries=["alpha"])
        chunks = [composition.Chunk(source_id="source:bbb", title="B", text="body")]
        prompt = composition.build_section_prompt(
            section, chunks, "report", "en", numbers={"source:bbb": 5}
        )
        assert "[5] B" in prompt
        assert "[source:5] (source: B)\nbody" in prompt


class TestComposeSection:
    @pytest.mark.asyncio
    async def test_text_is_returned_with_the_chunks_used(self):
        section = outline.Section(title="One", queries=["alpha"])
        chunks = [composition.Chunk(source_id="source:aaa", title="A", text="a")]
        complete = make_complete(["## One\nbody"])

        text, used = await composition.compose_section(
            complete, section, chunks, "report", composition.CompositionConfig()
        )
        assert text == "## One\nbody"
        assert used == chunks

    @pytest.mark.asyncio
    async def test_empty_reply_is_retried_with_half_the_material(self):
        section = outline.Section(title="One", queries=["alpha"])
        chunks = [
            composition.Chunk(source_id=f"source:{i}", title="T", text=f"t{i}")
            for i in range(4)
        ]
        complete = make_complete(["", "## One\nbody"])

        text, used = await composition.compose_section(
            complete, section, chunks, "report", composition.CompositionConfig()
        )
        assert text == "## One\nbody"
        assert [c.source_id for c in used] == ["source:0", "source:1"]

    @pytest.mark.asyncio
    async def test_a_single_attempt_config_never_retries(self):
        section = outline.Section(title="One", queries=["alpha"])
        chunks = [
            composition.Chunk(source_id=f"source:{i}", title="T", text=f"t{i}")
            for i in range(4)
        ]
        complete = make_complete(["", "## One\nbody"])
        cfg = composition.CompositionConfig(max_section_attempts=1)

        text, used = await composition.compose_section(
            complete, section, chunks, "report", cfg
        )
        assert text == ""
        assert used == chunks
        assert len(complete.prompts) == 1

    @pytest.mark.asyncio
    async def test_a_failing_call_degrades_to_empty_text(self):
        async def failing(prompt):
            raise RuntimeError("model down")

        section = outline.Section(title="One", queries=["alpha"])
        text, _ = await composition.compose_section(
            failing,
            section,
            [composition.Chunk(source_id="source:aaa", title="A", text="a")],
            "report",
            composition.CompositionConfig(),
        )
        assert text == ""


class TestBuildSectionPrompt:
    def test_deck_and_report_use_their_own_rules(self):
        section = outline.Section(title="One", thesis="t", queries=["alpha"])
        chunks = [composition.Chunk(source_id="source:aaa", title="A", text="body")]
        deck = composition.build_section_prompt(section, chunks, "deck", "it")
        report = composition.build_section_prompt(section, chunks, "report", "it")
        assert "one idea per bullet" in deck
        assert "one idea per bullet" not in report
        # A raw ISO code ("it") is ignored by the model; the prompt must carry
        # the language NAME.
        assert "Write in Italian" in deck
        assert "Write in it" not in deck

    def test_chunks_are_numbered_for_citation(self):
        section = outline.Section(title="One", queries=["alpha"])
        chunks = [
            composition.Chunk(source_id="source:aaa", title="A", text="first"),
            composition.Chunk(source_id="source:bbb", title="B", text="second"),
        ]
        prompt = composition.build_section_prompt(section, chunks, "report", "en")
        assert "[source:1] (source: A)\nfirst" in prompt
        assert "[source:2] (source: B)\nsecond" in prompt

    def test_no_chunks_is_stated_explicitly(self):
        section = outline.Section(title="One", queries=["alpha"])
        prompt = composition.build_section_prompt(section, [], "report", "en")
        assert "(no excerpt retrieved)" in prompt

    def test_diagram_rules_only_when_allowed(self):
        section = outline.Section(title="One", queries=["alpha"])
        assert "mermaid" not in composition.build_section_prompt(
            section, [], "report", "en"
        )
        assert "mermaid" in composition.build_section_prompt(
            section, [], "report", "en", allow_diagrams=True
        )


class TestBuildDocument:
    @pytest.mark.asyncio
    async def test_document_resolves_citations_and_drops_unknown_ones(self):
        sections = [outline.Section(title="One", queries=["alpha"])]
        search = make_search([make_hit()])
        complete = make_complete(["## One\nBody [source:1]. Bad [source:7]."])

        document, report = await composition.build_document(
            complete,
            search,
            [outline.SourceRef("source:aaa", "Source A")],
            "My title",
            "report",
            composition.RetrievalConfig(),
            composition.CompositionConfig(),
            sections,
        )

        assert document.startswith("# My title")
        assert "Body [1]." in document
        assert "[source:7]" not in document
        assert report["mode"] == "retrieval"
        assert report["sections_written"] == 1
        assert report["unknown_citations"] == ["7"]
        assert report["sections"][0]["chunks"][0]["source_id"] == "source:aaa"
        assert report["references"] == [
            {
                "number": 1,
                "source_id": "source:aaa",
                "title": "Source A",
                "url": "",
            }
        ]
        assert report["cited_numbers"] == [1]

    @pytest.mark.asyncio
    async def test_verification_can_be_disabled(self):
        cfg = composition.RetrievalConfig(verify_citations=False)
        document, _ = await composition.build_document(
            make_complete(["## One\n[source:9]"]),
            make_search([make_hit()]),
            [outline.SourceRef("source:aaa", "Source A")],
            "T",
            "report",
            cfg,
            composition.CompositionConfig(),
            [outline.Section(title="One", queries=["alpha"])],
        )
        assert "[source:9]" in document

    @pytest.mark.asyncio
    async def test_sections_producing_nothing_are_skipped(self):
        document, report = await composition.build_document(
            make_complete([""]),
            make_search([make_hit()]),
            [outline.SourceRef("source:aaa", "Source A")],
            "T",
            "report",
            composition.RetrievalConfig(),
            composition.CompositionConfig(max_section_attempts=1),
            [outline.Section(title="One", queries=["alpha"])],
        )
        assert "## One" not in document
        assert report["sections_written"] == 0

    @pytest.mark.asyncio
    async def test_outline_is_planned_when_no_sections_are_given(self, monkeypatch):
        reply = '{"sections": [{"title": "Planned", "queries": ["alpha"]}]}'

        class _Model:
            async def ainvoke(self, prompt):
                return SimpleNamespace(content=reply)

        async def fake_provision(content, model_id, default_type, **kwargs):
            return _Model()

        monkeypatch.setattr(outline, "provision_langchain_model", fake_provision)

        complete = make_complete(["## Planned\nBody [source:1]"])
        document, report = await composition.build_document(
            complete,
            make_search([make_hit()]),
            [outline.SourceRef("source:aaa", "Source A")],
            "T",
            "report",
            composition.RetrievalConfig(),
        )
        assert "## Planned" in document
        assert report["sections"][0]["title"] == "Planned"

    @pytest.mark.asyncio
    async def test_a_planned_bibliography_section_is_dropped(self):
        sections = [
            outline.Section(title="One", queries=["alpha"]),
            outline.Section(title="Sources", queries=["alpha"]),
        ]
        document, report = await composition.build_document(
            make_complete(["## One\nBody [source:1]"]),
            make_search([make_hit()]),
            [outline.SourceRef("source:aaa", "Source A")],
            "T",
            "report",
            composition.RetrievalConfig(),
            composition.CompositionConfig(),
            sections,
        )
        assert "## One" in document
        assert "## Sources" not in document
        assert report["sections_written"] == 1

    @pytest.mark.asyncio
    async def test_a_section_that_wrote_nothing_cites_nothing(self):
        sections = [
            outline.Section(title="One", queries=["alpha"]),
            outline.Section(title="Two", queries=["alpha"]),
        ]
        complete = make_complete(["## One\nBody [source:1]", ""])

        document, report = await composition.build_document(
            complete,
            make_search([make_hit()]),
            [outline.SourceRef("source:aaa", "Source A")],
            "T",
            "report",
            composition.RetrievalConfig(),
            composition.CompositionConfig(max_section_attempts=1),
            sections,
        )

        # Section Two retrieved the same excerpt but produced no text: its
        # source must not appear in the reference list.
        assert report["sections_written"] == 1
        assert report["cited_numbers"] == [1]


class TestAssembleAndConfig:
    def test_document_has_a_title_and_no_leading_blank_line(self):
        document = composition.assemble_document("T", ["a", "  ", "b"])
        assert document == "# T\n\na\n\nb\n"

    def test_document_without_a_title_starts_with_the_body(self):
        assert composition.assemble_document("", ["body"]) == "body\n"

    def test_config_defaults_match_the_standalone_config(self):
        cfg = composition.config_from_dict(None)
        assert cfg.outline_max_sections == 5
        assert cfg.min_score == 0.2
        assert cfg.chunks_per_query == 10
        assert cfg.max_chunks_per_section == 30
        assert cfg.max_chunks_per_source == 4
        assert cfg.max_chars_per_chunk == 2000
        assert cfg.max_chars_per_section == 40000

    def test_config_overrides_are_applied(self):
        cfg = composition.config_from_dict(
            {"min_score": 0.5, "verify_citations": False}
        )
        assert cfg.min_score == 0.5
        assert cfg.verify_citations is False


class TestBookScaleBudgets:
    """The defaults must fit a BOOK CHAPTER, not a slide-sized section."""

    def test_one_section_keeps_twenty_long_excerpts(self):
        hits = [
            make_hit(source_id=f"source:{i}", title="T", text="x" * 1500)
            for i in range(20)
        ]
        chunks = composition.select_chunks(hits, [], composition.RetrievalConfig())
        assert len(chunks) == 20

    def test_a_section_budget_is_tens_of_thousands_of_characters(self):
        cfg = composition.RetrievalConfig()
        assert cfg.max_chars_per_section >= 40000
        assert cfg.max_chunks_per_section >= 30
        assert cfg.chunks_per_query >= 10
        assert cfg.max_chars_per_chunk >= 2000
        assert cfg.max_chunks_per_source >= 4

    def test_the_writer_is_given_room_for_a_long_section(self):
        assert outline.DEFAULT_COMPLETION_MAX_TOKENS >= 16384
        assert outline.DEFAULT_OUTLINE_MAX_TOKENS >= 4096


class TestSectionFormatRules:
    """Bullets must not be forced: the shape follows the material."""

    def test_the_deck_allows_a_short_paragraph_when_a_list_would_distort(self):
        assert "short paragraph" in outline.SECTION_RULES_DECK

    def test_the_deck_does_not_fix_every_section_at_four_bullets(self):
        assert "4 to 6 bullets" not in outline.SECTION_RULES_DECK

    def test_a_deck_point_may_hold_an_idea_longer_than_eighteen_words(self):
        assert "max 18 words" not in outline.SECTION_RULES_DECK

    def test_the_report_does_not_cap_the_prose_at_four_lines(self):
        assert "max 4 lines" not in outline.SECTION_RULES_REPORT


class TestBookShape:
    """A document is a BOOK: a few broad chapters, a lot of prose."""

    def test_the_default_outline_is_only_a_handful_of_sections(self):
        assert outline.DEFAULT_MAX_SECTIONS <= 6
        assert composition.RetrievalConfig().outline_max_sections <= 6

    def test_the_report_rules_ask_for_a_long_chapter_of_prose(self):
        rules = outline.SECTION_RULES_REPORT
        assert "chapter" in rules
        assert "words" in rules
        assert "bullet" in rules

    def test_the_outline_prompt_asks_for_few_broad_chapters(self):
        assert "chapter" in outline.OUTLINE_PROMPT


class TestVariants:
    """NotebookLM-style sub-variants: report document|illustrated, deck presenter|detailed.

    The name must say what the deliverable IS. "Interactive" was rejected: in
    NotebookLM it means an embedded, playable Studio artifact, not a static
    figure, so our text-with-figures variant is called "illustrated".
    """

    def test_a_report_defaults_to_a_text_only_document(self):
        assert outline.normalize_variant("report", None) == "document"

    def test_a_deck_defaults_to_presenter_slides(self):
        assert outline.normalize_variant("deck", None) == "presenter"

    def test_a_variant_of_the_other_kind_is_rejected(self):
        with pytest.raises(ValueError):
            outline.normalize_variant("report", "presenter")

    def test_a_deck_variant_is_not_valid_for_a_report(self):
        assert sorted(outline.VARIANTS["report"]) == ["document", "illustrated"]
        assert sorted(outline.VARIANTS["deck"]) == ["detailed", "presenter"]

    def test_only_the_illustrated_report_is_given_diagrams(self):
        assert outline.variant_allows_diagrams("report", "document") is False
        assert outline.variant_allows_diagrams("report", "illustrated") is True
        assert outline.variant_allows_diagrams("deck", "presenter") is True
        assert outline.variant_allows_diagrams("deck", "detailed") is True

    def test_a_detailed_deck_asks_for_full_text_per_slide(self):
        section = outline.Section(title="One", queries=["q"])
        detailed = composition.build_section_prompt(
            section, [], "deck", "en", variant="detailed"
        )
        presenter = composition.build_section_prompt(
            section, [], "deck", "en", variant="presenter"
        )
        assert detailed != presenter
        assert "full sentences" in detailed
        assert "full sentences" not in presenter

    def test_an_illustrated_report_is_prose_with_diagrams(self):
        section = outline.Section(title="One", queries=["q"])
        illustrated = composition.build_section_prompt(
            section, [], "report", "en", variant="illustrated", allow_diagrams=True
        )
        assert "CHAPTER" in illustrated
        assert "mermaid" in illustrated
