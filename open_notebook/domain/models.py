from typing import ClassVar, Dict, Optional, Union

from esperanto import (
    AIFactory,
    EmbeddingModel,
    LanguageModel,
    SpeechToTextModel,
    TextToSpeechModel,
)

from open_notebook.database.repository import repo_query
from open_notebook.domain.base import ObjectModel, RecordModel

ModelType = Union[LanguageModel, EmbeddingModel, SpeechToTextModel, TextToSpeechModel]


class Model(ObjectModel):
    table_name: ClassVar[str] = "model"
    name: str
    provider: str
    type: str

    @classmethod
    async def get_models_by_type(cls, model_type):
        models = await repo_query(
            "SELECT * FROM model WHERE type=$model_type;", {"model_type": model_type}
        )
        return [Model(**model) for model in models]


class DefaultModels(RecordModel):
    record_id: ClassVar[str] = "open_notebook:default_models"
    default_chat_model: Optional[str] = None
    default_transformation_model: Optional[str] = None
    large_context_model: Optional[str] = None
    default_text_to_speech_model: Optional[str] = None
    default_speech_to_text_model: Optional[str] = None
    # default_vision_model: Optional[str]
    default_embedding_model: Optional[str] = None
    default_tools_model: Optional[str] = None


class ModelManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._model_cache: Dict[str, ModelType] = {}
            self._default_models = None

    async def get_model(self, model_id: str, **kwargs) -> Optional[ModelType]:
        if not model_id:
            return None

        cache_key = f"{model_id}:{str(kwargs)}"

        if cache_key in self._model_cache:
            cached_model = self._model_cache[cache_key]
            if not isinstance(
                cached_model,
                (LanguageModel, EmbeddingModel, SpeechToTextModel, TextToSpeechModel),
            ):
                raise TypeError(
                    f"Cached model is of unexpected type: {type(cached_model)}"
                )
            return cached_model

        try:
            model: Model = await Model.get(model_id)
        except Exception:
            raise ValueError(f"Model with ID {model_id} not found")

        if not model.type or model.type not in [
            "language",
            "embedding",
            "speech_to_text",
            "text_to_speech",
        ]:
            raise ValueError(f"Invalid model type: {model.type}")

        model_instance: ModelType
        if model.type == "language":
            model_instance = AIFactory.create_language(
                model_name=model.name,
                provider=model.provider,
                config=kwargs,
            )
        elif model.type == "embedding":
            model_instance = AIFactory.create_embedding(
                model_name=model.name,
                provider=model.provider,
                config=kwargs,
            )
        elif model.type == "speech_to_text":
            model_instance = AIFactory.create_speech_to_text(
                model_name=model.name,
                provider=model.provider,
                config=kwargs,
            )
        elif model.type == "text_to_speech":
            model_instance = AIFactory.create_text_to_speech(
                model_name=model.name,
                provider=model.provider,
                config=kwargs,
            )
        else:
            raise ValueError(f"Invalid model type: {model.type}")

        self._model_cache[cache_key] = model_instance
        return model_instance

    async def refresh_defaults(self):
        """Refresh the default models from the database"""
        self._default_models = await DefaultModels.get_instance()

    async def get_defaults(self) -> DefaultModels:
        """Get the default models configuration"""
        if not self._default_models:
            await self.refresh_defaults()
            if not self._default_models:
                raise RuntimeError("Failed to initialize default models configuration")
        return self._default_models

    async def get_speech_to_text(self, **kwargs) -> Optional[SpeechToTextModel]:
        """Get the default speech-to-text model"""
        defaults = await self.get_defaults()
        model_id = defaults.default_speech_to_text_model
        if not model_id:
            return None
        model = await self.get_model(model_id, **kwargs)
        assert model is None or isinstance(model, SpeechToTextModel), (
            f"Expected SpeechToTextModel but got {type(model)}"
        )
        return model

    async def get_text_to_speech(self, **kwargs) -> Optional[TextToSpeechModel]:
        """Get the default text-to-speech model"""
        defaults = await self.get_defaults()
        model_id = defaults.default_text_to_speech_model
        if not model_id:
            return None
        model = await self.get_model(model_id, **kwargs)
        assert model is None or isinstance(model, TextToSpeechModel), (
            f"Expected TextToSpeechModel but got {type(model)}"
        )
        return model

    async def get_embedding_model(self, **kwargs) -> Optional[EmbeddingModel]:
        """Get the default embedding model"""
        defaults = await self.get_defaults()
        model_id = defaults.default_embedding_model
        if not model_id:
            return None
        model = await self.get_model(model_id, **kwargs)
        assert model is None or isinstance(model, EmbeddingModel), (
            f"Expected EmbeddingModel but got {type(model)}"
        )
        return model

    async def get_default_model(self, model_type: str, **kwargs) -> Optional[ModelType]:
        """
        Get the default model for a specific type.

        Args:
            model_type: The type of model to retrieve (e.g., 'chat', 'embedding', etc.)
            **kwargs: Additional arguments to pass to the model constructor
        """
        defaults = await self.get_defaults()
        model_id = None

        if model_type == "chat":
            model_id = defaults.default_chat_model
        elif model_type == "transformation":
            model_id = (
                defaults.default_transformation_model
                or defaults.default_chat_model
            )
        elif model_type == "tools":
            model_id = (
                defaults.default_tools_model or defaults.default_chat_model
            )
        elif model_type == "embedding":
            model_id = defaults.default_embedding_model
        elif model_type == "text_to_speech":
            model_id = defaults.default_text_to_speech_model
        elif model_type == "speech_to_text":
            model_id = defaults.default_speech_to_text_model
        elif model_type == "large_context":
            model_id = defaults.large_context_model

        if not model_id:
            return None

        return await self.get_model(model_id, **kwargs)

    def clear_cache(self):
        """Clear the model cache"""
        self._model_cache.clear()


model_manager = ModelManager()
