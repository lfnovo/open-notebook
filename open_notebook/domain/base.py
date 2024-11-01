from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional, Type, TypeVar

from loguru import logger
from pydantic import BaseModel, ValidationError, field_validator

from open_notebook.database.repository import (
    repo_create,
    repo_delete,
    repo_query,
    repo_relate,
    repo_update,
)
from open_notebook.exceptions import (
    DatabaseOperationError,
    InvalidInputError,
    NotFoundError,
)

T = TypeVar("T", bound="ObjectModel")


class ObjectModel(BaseModel):
    id: Optional[str] = None
    table_name: ClassVar[str] = ""
    created: Optional[datetime] = None
    updated: Optional[datetime] = None

    @classmethod
    def get_all(cls: Type[T], order_by=None) -> List[T]:
        try:
            if order_by:
                order = f" ORDER BY {order_by}"
            else:
                order = ""
            result = repo_query(f"SELECT * FROM {cls.table_name} {order}")
            objects = []
            for obj in result:
                try:
                    objects.append(cls(**obj))
                except Exception as e:
                    logger.critical(f"Error creating object: {str(e)}")

            return objects
        except Exception as e:
            logger.error(f"Error fetching all {cls.table_name}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(e)

    @classmethod
    def get(cls: Type[T], id: str) -> T:
        if not id:
            raise InvalidInputError("ID cannot be empty")
        try:
            result = repo_query(f"SELECT * FROM {id}")
            if result:
                return cls(**result[0])
            return None
        except Exception as e:
            logger.error(f"Error fetching {cls.table_name} with id {id}: {str(e)}")
            logger.exception(e)
            raise NotFoundError(f"{cls.table_name} with id {id} not found")

    def needs_embedding(self) -> bool:
        return False

    def get_embedding_content(self) -> Optional[str]:
        return None

    def save(self) -> None:
        from open_notebook.config import load_default_models

        DEFAULT_MODELS, EMBEDDING_MODEL, SPEECH_TO_TEXT_MODEL = load_default_models()

        try:
            logger.debug(f"Validating {self.__class__.__name__}")
            self.model_validate(self.model_dump(), strict=True)
            data = self._prepare_save_data()
            data["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if self.needs_embedding():
                embedding_content = self.get_embedding_content()
                if embedding_content:
                    data["embedding"] = EMBEDDING_MODEL.embed(embedding_content)

            if self.id is None:
                data["created"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.debug("Creating new record")
                repo_result = repo_create(self.__class__.table_name, data)
            else:
                data["created"] = self.created.strftime("%Y-%m-%d %H:%M:%S")
                logger.debug(f"Updating record with id {self.id}")
                repo_result = repo_update(self.id, data)

            # Update the current instance with the result
            for key, value in repo_result[0].items():
                if hasattr(self, key):
                    if isinstance(getattr(self, key), BaseModel):
                        setattr(self, key, type(getattr(self, key))(**value))
                    else:
                        setattr(self, key, value)

        except ValidationError as e:
            logger.error(f"Validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Error saving record: {e}")
            raise

        except Exception as e:
            logger.error(f"Error saving {self.__class__.table_name}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(e)

    def _prepare_save_data(self) -> Dict[str, Any]:
        data = self.model_dump()
        # del data["created"]
        # del data["updated"]
        return {key: value for key, value in data.items() if value is not None}

    def delete(self) -> bool:
        if self.id is None:
            raise InvalidInputError("Cannot delete object without an ID")
        try:
            logger.debug(f"Deleting record with id {self.id}")
            return repo_delete(self.id)
        except Exception as e:
            logger.error(
                f"Error deleting {self.__class__.table_name} with id {self.id}: {str(e)}"
            )
            raise DatabaseOperationError(
                f"Failed to delete {self.__class__.table_name}"
            )

    def relate(self, relationship: str, target_id: str) -> Any:
        if not relationship or not target_id or not self.id:
            raise InvalidInputError("Relationship and target ID must be provided")
        try:
            return repo_relate(self.id, relationship, target_id)
        except Exception as e:
            logger.error(f"Error creating relationship: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(e)

    @field_validator("created", "updated", mode="before")
    @classmethod
    def parse_datetime(cls, value):
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value
