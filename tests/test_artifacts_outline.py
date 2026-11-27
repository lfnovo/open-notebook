"""Unit tests for the artifact outline planner.

The language model is replaced by a canned offline stub
(``provision_langchain_model`` is monkeypatched), so nothing here touches the
network or the database.
"""

from types import SimpleNamespace

import pytest

from open_notebook.artifacts import outline

VALID_REPLY = (
    '{"sections": ['
    '{"title": "Intro", "thesis": "the claim", "queries": ["alpha", "beta"]},'
    '{"title": "Deep dive", "thesis": "more", "queries": ["gamma"]}'
    "]}"
)

FENCED_REPLY = "```json\n" + VALID_REPLY + "\n```"


class _FakeModel:
    """Minimal stand-in for the provisioned langchain chat model."""

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.prompts: list[str] = []

    async def ainvoke(self, prompt: str) -> SimpleNamespace:
        """Record the prompt and answer with the canned reply."""
        self.prompts.append(prompt)
        return SimpleNamespace(content=self.reply)


def _patch_model(monkeypatch: pytest.MonkeyPatch, reply: str) -> _FakeModel:
    """Replace provision_langchain_model() with an offline canned model."""
    model = _FakeModel(reply)

    async def fake_provision(content, model_id, default_type, **kwargs):
        return model

    monkeypatch.setattr(outline, "provision_langchain_model", fake_provision)
    return model


class TestKindHelpers:
    def test_deck_and_legacy_slides_map_to_deck(self):
        assert outline.normalize_kind("deck") == "deck"
        assert outline.normalize_kind("slides") == "deck"
        assert outline.kind_label("deck") == "a slide presentation"

    def test_unknown_or_missing_kind_falls_back_to_report(self):
        assert outline.normalize_kind("report") == "report"
        assert outline.normalize_kind(None) == "report"
        assert outline.normalize_kind("quiz") == "report"
        assert outline.kind_label("report") == "a report"


class TestBuildOutlinePrompt:
    def test_prompt_lists_sources_rules_and_the_cap(self):
        prompt = outline.build_outline_prompt(
            ["Source A", "", "Source B"], "My title", "report", "", 4
        )
        assert "- Source A" in prompt
        assert "- Source B" in prompt
        assert "My title" in prompt
        assert "AT MOST 4 sections" in prompt
        assert '{"sections"' in prompt

    def test_prompt_without_sources_says_so(self):
        assert "no title" in outline.build_outline_prompt([], "", "deck")

    def test_instructions_are_inserted_only_when_present(self):
        without = outline.build_outline_prompt(["S"], "T", "deck")
        assert "USER INSTRUCTIONS" not in without
        with_brief = outline.build_outline_prompt(["S"], "T", "deck", "focus on X")
        assert "focus on X" in with_brief
        assert "USER INSTRUCTIONS" in with_brief


class TestParseOutline:
    def test_valid_json_is_parsed_in_order(self):
        sections = outline.parse_outline(VALID_REPLY, 10)
        assert [s.title for s in sections] == ["Intro", "Deep dive"]
        assert sections[0].thesis == "the claim"
        assert sections[0].queries == ["alpha", "beta"]

    def test_fenced_json_is_parsed(self):
        assert len(outline.parse_outline(FENCED_REPLY, 10)) == 2

    def test_reply_with_surrounding_prose_is_parsed(self):
        sections = outline.parse_outline("Sure! " + VALID_REPLY + " Done.", 10)
        assert len(sections) == 2

    def test_sections_are_capped(self):
        sections = outline.parse_outline(VALID_REPLY, 1)
        assert [s.title for s in sections] == ["Intro"]

    def test_missing_queries_fall_back_to_the_title(self):
        reply = '{"sections": [{"title": "Only title", "thesis": ""}]}'
        sections = outline.parse_outline(reply, 10)
        assert sections[0].queries == ["Only title"]

    def test_titles_without_content_are_skipped(self):
        reply = '{"sections": [{"queries": ["x"]}, {"title": "Kept"}]}'
        assert [s.title for s in outline.parse_outline(reply, 10)] == ["Kept"]

    def test_reply_without_json_object_raises(self):
        with pytest.raises(ValueError, match="no JSON object"):
            outline.parse_outline("no json here", 10)

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="not valid JSON"):
            outline.parse_outline('{"sections": [}', 10)

    def test_missing_sections_list_raises(self):
        with pytest.raises(ValueError, match="no 'sections' list"):
            outline.parse_outline('{"other": []}', 10)

    def test_empty_sections_list_raises(self):
        with pytest.raises(ValueError, match="no 'sections' list"):
            outline.parse_outline('{"sections": []}', 10)

    def test_reply_with_no_usable_section_raises(self):
        with pytest.raises(ValueError, match="no usable section"):
            outline.parse_outline('{"sections": [{"thesis": "x"}]}', 10)


class TestFallbackOutline:
    def test_fallback_uses_the_fixed_skeleton(self):
        sections = outline.fallback_outline("My title", 3)
        assert [s.title for s in sections] == ["Overview", "Key points", "Details"]

    def test_fallback_queries_include_the_document_title(self):
        sections = outline.fallback_outline("My title", 2)
        assert sections[0].queries == ["My title", "Overview"]

    def test_fallback_without_a_title_uses_the_section_title_only(self):
        assert outline.fallback_outline("", 1)[0].queries == ["Overview"]


class TestPlanOutline:
    @pytest.mark.asyncio
    async def test_valid_reply_becomes_sections(self, monkeypatch):
        model = _patch_model(monkeypatch, VALID_REPLY)
        sections = await outline.plan_outline(["Source A"], "Title", "deck")
        assert [s.title for s in sections] == ["Intro", "Deep dive"]
        assert len(model.prompts) == 1

    @pytest.mark.asyncio
    async def test_invalid_json_falls_back_instead_of_raising(self, monkeypatch):
        _patch_model(monkeypatch, "I am not JSON at all")
        sections = await outline.plan_outline(["Source A"], "Title", "report", "", 2)
        assert [s.title for s in sections] == ["Overview", "Key points"]

    @pytest.mark.asyncio
    async def test_capped_fallback_respects_max_sections(self, monkeypatch):
        _patch_model(monkeypatch, "{broken")
        sections = await outline.plan_outline(["Source A"], "Title", "report", "", 1)
        assert [s.title for s in sections] == ["Overview"]


class TestCompleteText:
    @pytest.mark.asyncio
    async def test_thinking_blocks_and_fences_are_stripped(self, monkeypatch):
        reply = "<think>secret reasoning</think>```markdown\n# Body\n```"
        _patch_model(monkeypatch, reply)
        assert await outline.complete_text("prompt") == "# Body"

    @pytest.mark.asyncio
    async def test_plain_reply_is_returned_unchanged(self, monkeypatch):
        _patch_model(monkeypatch, "  hello  ")
        assert await outline.complete_text("prompt") == "hello"

    @pytest.mark.asyncio
    async def test_structured_content_parts_are_joined(self, monkeypatch):
        model = _patch_model(monkeypatch, "")

        async def structured(prompt: str) -> SimpleNamespace:
            return SimpleNamespace(content=[{"type": "text", "text": "# Joined"}])

        monkeypatch.setattr(model, "ainvoke", structured)
        assert await outline.complete_text("prompt") == "# Joined"


class TestOutputBudgets:
    """The output budget must be explicit: the provisioned default (850 tokens,
    measured) is spent entirely by a reasoning model's thinking block, and the
    reply then comes back empty with ``finish_reason=length``."""

    @pytest.mark.asyncio
    async def test_complete_text_sends_the_completion_budget(self, monkeypatch):
        captured: dict = {}

        async def fake_provision(content, model_id, default_type, **kwargs):
            captured.update(kwargs)
            return _FakeModel("ok")

        monkeypatch.setattr(outline, "provision_langchain_model", fake_provision)

        await outline.complete_text("prompt")

        assert captured["max_tokens"] == outline.DEFAULT_COMPLETION_MAX_TOKENS

    @pytest.mark.asyncio
    async def test_complete_text_accepts_an_explicit_budget(self, monkeypatch):
        captured: dict = {}

        async def fake_provision(content, model_id, default_type, **kwargs):
            captured.update(kwargs)
            return _FakeModel("ok")

        monkeypatch.setattr(outline, "provision_langchain_model", fake_provision)

        await outline.complete_text("prompt", max_tokens=123)

        assert captured["max_tokens"] == 123

    @pytest.mark.asyncio
    async def test_plan_outline_uses_the_outline_budget(self, monkeypatch):
        captured: dict = {}

        async def fake_complete(
            prompt, model_id=None, default_type="chat", max_tokens=None
        ):
            captured["max_tokens"] = max_tokens
            return VALID_REPLY

        monkeypatch.setattr(outline, "complete_text", fake_complete)

        sections = await outline.plan_outline(["Source A"], "Title", "report")

        assert captured["max_tokens"] == outline.DEFAULT_OUTLINE_MAX_TOKENS
        assert [s.title for s in sections] == ["Intro", "Deep dive"]

    def test_both_budgets_are_above_the_provisioned_default(self):
        assert outline.DEFAULT_OUTLINE_MAX_TOKENS > 850
        assert outline.DEFAULT_COMPLETION_MAX_TOKENS > 850


class TestOutlineRetry:
    """A single unusable planner reply must not drop the document onto the
    generic English skeleton: the planning call is retried."""

    @pytest.mark.asyncio
    async def test_bad_first_reply_is_retried(self, monkeypatch):
        replies = iter(["{broken", VALID_REPLY])

        async def fake_complete(
            prompt, model_id=None, default_type="chat", max_tokens=None
        ):
            return next(replies)

        monkeypatch.setattr(outline, "complete_text", fake_complete)

        sections = await outline.plan_outline(["Source A"], "Title", "report")

        assert [s.title for s in sections] == ["Intro", "Deep dive"]

    @pytest.mark.asyncio
    async def test_every_bad_reply_falls_back_to_the_skeleton(self, monkeypatch):
        calls: dict = {"n": 0}

        async def fake_complete(
            prompt, model_id=None, default_type="chat", max_tokens=None
        ):
            calls["n"] += 1
            return "{broken"

        monkeypatch.setattr(outline, "complete_text", fake_complete)

        sections = await outline.plan_outline(["Source A"], "Title", "report", "", 2)

        assert calls["n"] == outline.DEFAULT_OUTLINE_ATTEMPTS
        assert [s.title for s in sections] == ["Overview", "Key points"]


class TestLanguageName:
    """A raw ISO code ("it") is ignored by the model; the prompts must carry
    the language NAME."""

    def test_codes_become_names(self):
        assert outline.language_name("it") == "Italian"
        assert outline.language_name("EN") == "English"
        assert outline.language_name("zh") == "Chinese"

    def test_names_and_unknown_values_pass_through(self):
        assert outline.language_name("Italian") == "Italian"
        assert outline.language_name("Klingon") == "Klingon"
        assert outline.language_name("") == ""

    def test_outline_prompt_states_the_language_by_name(self):
        prompt = outline.build_outline_prompt(["S"], "T", "report", "", 4, "it")
        assert "Write the section titles in Italian" in prompt

    def test_outline_prompt_omits_the_language_when_unset(self):
        prompt = outline.build_outline_prompt(["S"], "T", "report")
        assert "Write the section titles" not in prompt
