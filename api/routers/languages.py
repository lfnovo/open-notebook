from typing import List

import pycountry
from babel import Locale
from babel.core import get_global
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# Additional regional variants for languages where the distinction matters
# (TTS accent, vocabulary, spelling differences)
_EXTRA_VARIANTS = [
    "pt_PT",
    "en_GB",
    "en_AU",
    "en_IN",
    "es_MX",
    "es_AR",
    "es_CO",
    "fr_CA",
    "fr_CH",
    "zh_TW",
    "zh_HK",
    "de_AT",
    "de_CH",
    "ar_SA",
    "nl_BE",
]


class LanguageResponse(BaseModel):
    code: str
    name: str


@router.get("/languages", response_model=List[LanguageResponse])
async def list_languages():
    """List available languages as BCP 47 locale codes (e.g. pt-BR, en-US)."""
    likely_subtags = get_global("likely_subtags")
    languages = []
    seen = set()

    # 1. For each language, resolve its default locale via CLDR likely subtags
    for lang in pycountry.languages:
        if not hasattr(lang, "alpha_2"):
            continue

        code = lang.alpha_2
        likely = likely_subtags.get(code)

        if likely:
            try:
                loc = Locale.parse(likely)
                if loc.territory:
                    bcp47 = f"{loc.language}-{loc.territory}"
                    display = loc.get_display_name("en")
                    if bcp47 not in seen:
                        seen.add(bcp47)
                        languages.append(LanguageResponse(code=bcp47, name=display))
                    continue
            except Exception:
                pass

        # Fallback: bare language code
        if code not in seen:
            seen.add(code)
            languages.append(LanguageResponse(code=code, name=lang.name))

    # 2. Add important regional variants
    for locale_str in _EXTRA_VARIANTS:
        try:
            loc = Locale.parse(locale_str)
            bcp47 = f"{loc.language}-{loc.territory}"
            if bcp47 not in seen:
                seen.add(bcp47)
                display = loc.get_display_name("en")
                languages.append(LanguageResponse(code=bcp47, name=display))
        except Exception:
            pass

    languages.sort(key=lambda x: x.name)
    return languages
