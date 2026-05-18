import os

from open_notebook.ai.key_provider import provision_provider_keys
from open_notebook.ai.models import Model
from open_notebook.exceptions import ConfigurationError
from open_notebook.multimodal.base import VideoUnderstandingProvider
from open_notebook.multimodal.providers.openai_compatible_video import (
    OpenAICompatibleVideoProvider,
)


async def get_video_understanding_provider(
    model: Model,
) -> VideoUnderstandingProvider:
    provider = model.provider.replace("-", "_").lower()

    config: dict = {}
    if model.credential:
        credential = await model.get_credential_obj()
        if credential:
            config = credential.to_esperanto_config()
    else:
        await provision_provider_keys(provider)

    if provider == "openai_compatible":
        return OpenAICompatibleVideoProvider(
            model_name=model.name,
            base_url=config.get("base_url") or os.environ.get("OPENAI_COMPATIBLE_BASE_URL"),
            api_key=config.get("api_key") or os.environ.get("OPENAI_COMPATIBLE_API_KEY"),
        )

    raise ConfigurationError(
        f"Provider '{model.provider}' does not support video_understanding yet"
    )
