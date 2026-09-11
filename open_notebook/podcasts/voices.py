"""Voice-id pre-flight against the TTS provider's own voice catalogue.

Speaker profiles store a free-text `voice_id` per speaker while the live TTS
model is whatever `voice_model` points at, and nothing ties the two together:
`SpeakerProfile.validate_speakers` only checks that the key exists. Migration 7
seeds three profiles with OpenAI voice names (`nova`, `alloy`, `echo`,
`shimmer`, `ash`), so a deployment whose voice model is Gemini inherits
speakers that can only work with OpenAI.

Without a pre-flight the mismatch surfaces only when the first audio clip is
generated - after the whole transcript has been generated and paid for - and
the provider error rarely names the voice: Gemini's 3.x TTS preview answers an
unknown voice with `404 Requested entity was not found.`, which reads like a
missing model (see #1238).

esperanto publishes each provider's catalogue as `available_voices`, so the
check is free for providers that hard-code their voice list (OpenAI,
Google/Gemini, Vertex, xAI, Mistral, Azure). For providers that fetch it over
HTTP (ElevenLabs, OpenRouter, OpenAI-compatible endpoints) the lookup runs in a
worker thread with a timeout, and any failure means "catalogue unknown": an
unavailable catalogue must never block a generation that would otherwise work.

Those catalogues can also be stale - esperanto's OpenAI list predates `ash`,
`coral` and friends, which the OpenAI API accepts - so "absent from the
catalogue" alone is NOT treated as an error. Only a voice that another
provider's catalogue does list is reported as a mismatch: that is the seeded
OpenAI-voice-on-Gemini case, and it cannot work. Anything else is logged and
allowed through.
"""

import asyncio
import hashlib
import json
from typing import Dict, NamedTuple, Optional, Set, Tuple

from loguru import logger

# The catalogue is a hard-coded dict for most providers; only the HTTP-backed
# ones can block, and a podcast run is not worth delaying for a pre-flight.
CATALOGUE_TIMEOUT_SECONDS = 10.0

# How often one validation pass will try a catalogue that keeps failing. Two
# attempts survive a one-off timeout without letting a dead endpoint charge
# CATALOGUE_TIMEOUT_SECONDS once per speaker (see VoiceCatalogueCache.get).
MAX_CATALOGUE_ATTEMPTS = 2

# Providers whose esperanto catalogue is a literal dict AND whose client can be
# constructed from placeholder credentials, so enumerating them costs nothing.
# Used only to attribute a voice to the provider it actually belongs to.
#
# Two deliberate omissions:
# - Mistral: available_voices paginates through GET /audio/voices, so listing it
#   sent a request (and a 401) to a provider the deployment may not even use.
# - Vertex: its catalogue is a literal dict, but the client needs real Google
#   credentials to construct, so every attribution attempt failed and spent the
#   retry budget on installs without them.
STATIC_CATALOGUE_PROVIDERS = ("openai", "google", "xai", "azure", "deepgram")

# Placeholder credentials: enough for the providers' constructors, never used
# for a request, since the catalogue is a literal dict.
_CATALOGUE_ONLY_CONFIG = {"api_key": "unused-catalogue-lookup"}

# Per-provider extras. Kept out of the shared dict because the keys are not
# interchangeable - Google's constructor rejects an unexpected `endpoint`
# outright, while Azure refuses to build without one.
_CATALOGUE_ONLY_EXTRAS = {
    "azure": {
        "base_url": "https://catalogue-lookup.invalid",
        "api_version": "2024-02-01",
    },
}


def catalogue_only_config(provider: str) -> dict:
    """Credentials good enough to read `provider`'s catalogue and nothing else."""
    return {**_CATALOGUE_ONLY_CONFIG, **_CATALOGUE_ONLY_EXTRAS.get(provider, {})}


class VoiceMismatch(NamedTuple):
    """A speaker voice_id the resolved TTS model does not list."""

    voice_id: str
    provider: str
    model_name: str
    known_voices: Set[str]
    # Providers whose catalogue DOES list this voice. Non-empty means the
    # mismatch is certain (the voice belongs to someone else), which is the
    # case worth failing the run for.
    other_providers: Set[str]

    @property
    def confident(self) -> bool:
        return bool(self.other_providers)


async def get_known_voice_ids(
    provider: str, model_name: Optional[str] = None, config: Optional[dict] = None
) -> Optional[Set[str]]:
    """Return the lower-cased voice ids `provider`/`model_name` accepts.

    Returns None when the catalogue can't be determined (provider unknown to
    esperanto, credentials missing, HTTP lookup failing or timing out, empty
    catalogue). Callers must treat None as "skip validation", never as "no
    voice is valid".

    Ids are lower-cased because providers accept them case-insensitively:
    Gemini lists `achernar` and accepts `Kore` (its documented capitalisation)
    for the same voice.
    """

    def _lookup() -> Set[str]:
        from esperanto import AIFactory

        model = AIFactory.create_text_to_speech(
            provider, model_name, config=config or {}
        )
        catalogue = model.available_voices or {}
        ids = {str(key).lower() for key in catalogue}
        ids.update(
            str(voice.id).lower()
            for voice in catalogue.values()
            if getattr(voice, "id", None)
        )
        return ids

    try:
        voice_ids = await asyncio.wait_for(
            asyncio.to_thread(_lookup), timeout=CATALOGUE_TIMEOUT_SECONDS
        )
    except Exception as e:
        logger.debug(
            f"Skipping voice validation for {provider}/{model_name}: "
            f"voice catalogue unavailable ({e})"
        )
        return None

    return voice_ids or None


def config_fingerprint(config: Optional[dict]) -> str:
    """Digest the credential config so two endpoints never share a catalogue.

    Sorted recursively - json.dumps(sort_keys=True) descends into nested dicts,
    where sorting only the top level would give one config two digests
    depending on how a nested mapping happened to be ordered. Values that
    aren't JSON-serializable fall back to repr(). Hashed rather than stored
    verbatim: the config carries API keys, and this value ends up in cache keys
    that can surface in reprs and tracebacks.
    """
    if not config:
        return ""
    canonical = json.dumps(config, sort_keys=True, default=repr)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


class VoiceCatalogueCache:
    """Memoizes catalogues for one validation pass.

    A catalogue can't change between the speakers of a single profile, but the
    HTTP-backed providers charge a request (up to CATALOGUE_TIMEOUT_SECONDS) for
    every lookup, and the cross-provider attribution below enumerates five more
    catalogues per mismatch. Without this, a 4-speaker ElevenLabs profile made
    the same request four times before generation could start.

    The key includes the credential config, not just provider and model name:
    speakers can override `voice_model` individually, and two Model records
    sharing a provider and model name may still point at different endpoints or
    accounts (`base_url`, `endpoint_tts`, a second API key). An ElevenLabs voice
    library is per-account, so reusing one account's catalogue for another would
    validate a speaker against voices it cannot use.

    Deliberately per-pass rather than process-wide: a fetched catalogue reflects
    the credentials in use, and a run should see voices added since the last one.
    """

    def __init__(self) -> None:
        self._catalogues: Dict[Tuple[str, Optional[str], str], Set[str]] = {}
        self._attempts: Dict[Tuple[str, Optional[str], str], int] = {}

    async def get(
        self, provider: str, model_name: Optional[str] = None, config: Optional[dict] = None
    ) -> Optional[Set[str]]:
        """Return the catalogue, fetching it at most MAX_CATALOGUE_ATTEMPTS times.

        Only successes are memoized. A failure is indistinguishable from an
        absent catalogue here - get_known_voice_ids() returns None for a timeout
        and for a provider esperanto doesn't know alike - so remembering the
        first failure would silently disable validation for every later speaker
        after one flaky request. Retrying without a bound would instead pay
        CATALOGUE_TIMEOUT_SECONDS per speaker whenever the endpoint is simply
        down, which is what this cache exists to avoid.
        """
        key = (provider, model_name, config_fingerprint(config))
        cached = self._catalogues.get(key)
        if cached is not None:
            return cached

        if self._attempts.get(key, 0) >= MAX_CATALOGUE_ATTEMPTS:
            return None
        self._attempts[key] = self._attempts.get(key, 0) + 1

        voice_ids = await get_known_voice_ids(provider, model_name, config)
        if voice_ids:
            self._catalogues[key] = voice_ids
        return voice_ids


async def find_voice_mismatch(
    provider: str,
    model_name: str,
    config: Optional[dict],
    voice_id: str,
    cache: Optional[VoiceCatalogueCache] = None,
) -> Optional[VoiceMismatch]:
    """Report a voice the model does not list, or None when it looks usable.

    Pass a shared `cache` when checking several speakers so each catalogue is
    fetched once for the whole profile.
    """
    cache = cache or VoiceCatalogueCache()

    known_voices = await cache.get(provider, model_name, config)
    if not known_voices:
        return None
    if voice_id.lower() in known_voices:
        return None

    other_providers = set()
    for other in STATIC_CATALOGUE_PROVIDERS:
        if other == provider:
            continue
        other_voices = await cache.get(other, config=catalogue_only_config(other))
        if other_voices and voice_id.lower() in other_voices:
            other_providers.add(other)

    return VoiceMismatch(
        voice_id=voice_id,
        provider=provider,
        model_name=model_name,
        known_voices=known_voices,
        other_providers=other_providers,
    )


def format_voice_list(voice_ids: Set[str], limit: int = 25) -> str:
    """Render a catalogue for an error message, capped so it stays readable."""
    ordered = sorted(voice_ids)
    if len(ordered) <= limit:
        return ", ".join(ordered)
    return ", ".join(ordered[:limit]) + f", … ({len(ordered)} total)"
