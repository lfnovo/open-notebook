"""Content-core adapter for the public model-admission contract.

Content-core constructs speech models itself and has a fallback provider. Both
slots must be closed on denial; otherwise a disabled local model could fall back
to a paid provider. Text/document extraction remains available.
"""
from open_notebook.modules.registry import ModuleError
from open_notebook.modules.runtime import model_policy

DENIED_PROVIDER = "open-notebook-module-disabled"


class ContentAudioAdapter:
    def configure(self, provider: str, name: str) -> dict:
        try:
            defaults = model_policy(provider, name, "speech_to_text")
        except ModuleError as error:
            if error.status != 409:
                raise
            # Unsupported provider is rejected by Esperanto BEFORE any network
            # request. It is set in BOTH paths, including content-core fallback.
            return {"audio_provider": DENIED_PROVIDER, "audio_model": name,
                    "stt_provider": DENIED_PROVIDER, "stt_model": name}
        result = {"audio_provider": provider.replace("_", "-"), "audio_model": name}
        if "timeout" in defaults:
            result["stt_timeout"] = defaults["timeout"]
        return result
