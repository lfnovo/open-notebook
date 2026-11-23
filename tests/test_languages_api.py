"""`GET /api/languages` must always return a usable name."""

import pytest
from babel import Locale

from api.routers import languages as languages_module


@pytest.mark.asyncio
async def test_languages_falls_back_to_the_code_when_babel_has_no_name(monkeypatch):
    """Some locales have no CLDR display name; the code stands in for it."""
    original = Locale.get_display_name

    def fake_display_name(self, locale=None, *args, **kwargs):
        if self.language == "en":
            return None
        return original(self, locale, *args, **kwargs)

    monkeypatch.setattr(Locale, "get_display_name", fake_display_name)

    result = await languages_module.list_languages()

    assert result, "expected languages"
    assert all(language.name for language in result)
    named_by_code = [language for language in result if language.name == language.code]
    assert named_by_code
    assert any(language.code.startswith("en-") for language in named_by_code)
