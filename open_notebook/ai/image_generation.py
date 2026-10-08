"""Image API adapter; Esperanto currently exposes no image-generation modality."""

import os

from openai import AsyncOpenAI

from open_notebook.ai.models import Model, _revalidate_config_urls, model_manager
from open_notebook.domain.credential import Credential
from open_notebook.exceptions import ConfigurationError, ExternalServiceError
from open_notebook.utils.chat_images import ChatImage


async def generate_chat_image(
    prompt: str, caption: str, model_id: str | None
) -> ChatImage:
    # Prefer the selected chat model's account. A separate image account can be
    # selected by ID without exporting keys or mutating process-wide env vars.
    credential_id = os.environ.get("OPEN_NOTEBOOK_IMAGE_CREDENTIAL_ID")
    config: dict = {}
    if credential_id:
        credential = await Credential.get(credential_id)
        if credential.provider not in {"openai", "openai_compatible"}:
            raise ConfigurationError(
                "Image generation requires an OpenAI-compatible credential."
            )
        config = credential.to_esperanto_config()
    else:
        if not model_id:
            model_id = (await model_manager.get_defaults()).default_chat_model
        if model_id:
            model = await Model.get(model_id)
            if model.provider in {"openai", "openai_compatible"}:
                credential = await model.get_credential_obj()
                if model.credential and credential is None:
                    raise ConfigurationError(
                        "The selected image credential could not be loaded."
                    )
                if credential:
                    config = credential.to_esperanto_config()
    api_key = config.get("api_key") or os.environ.get("OPENAI_API_KEY")
    base_url = config.get("base_url") or os.environ.get("OPENAI_BASE_URL")
    if not api_key:
        raise ConfigurationError(
            "Configure an OpenAI credential to generate images, or set OPEN_NOTEBOOK_IMAGE_CREDENTIAL_ID."
        )
    if base_url:
        await _revalidate_config_urls({"base_url": base_url}, "openai_compatible")
    async with AsyncOpenAI(
        api_key=api_key, base_url=base_url, timeout=180, max_retries=0
    ) as client:
        response = await client.images.generate(
            model=os.environ.get("OPEN_NOTEBOOK_IMAGE_MODEL", "gpt-image-1.5"),
            prompt=prompt,
            size="1024x1024",
            quality="low",
            output_format="png",
            n=1,
        )
    if not response.data or not response.data[0].b64_json:
        raise ExternalServiceError("The image provider returned no image.")
    return ChatImage(
        name=caption[:255] or "image.png",
        data_url=f"data:image/png;base64,{response.data[0].b64_json}",
        kind="generated",
    )
