import os
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Literal, Optional, Type, TypeVar

from langchain_core.runnables.config import RunnableConfig
from loguru import logger
from pydantic import BaseModel, Field, field_validator

from open_notebook.exceptions import (
    DatabaseOperationError,
    InvalidInputError,
    NotFoundError,
)
from open_notebook.graphs.summary import graph as summarizer
from open_notebook.repository import (
    repo_create,
    repo_delete,
    repo_query,
    repo_relate,
    repo_update,
)
from open_notebook.utils import get_embedding, split_text, surreal_clean

T = TypeVar("T", bound="ObjectModel")


class ObjectModel(BaseModel):
    id: Optional[str] = None
    table_name: ClassVar[str] = ""
    created: Optional[datetime] = None
    updated: Optional[datetime] = None

    @classmethod
    def get_all(cls: Type[T]) -> List[T]:
        try:
            result = repo_query(f"SELECT * FROM {cls.table_name}")
            objects = [cls(**obj) for obj in result]
            return objects
        except Exception as e:
            logger.error(f"Error fetching all {cls.table_name}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(f"Failed to fetch all {cls.table_name}")

    @classmethod
    def get(cls: Type[T], id: str) -> Optional[T]:
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
        try:
            data = self._prepare_save_data()

            if self.needs_embedding():
                embedding_content = self.get_embedding_content()
                if embedding_content:
                    data["embedding"] = get_embedding(embedding_content)

            if self.id is None:
                logger.debug("Creating new record")
                repo_result = repo_create(self.__class__.table_name, data)
            else:
                logger.debug(f"Updating record with id {self.id}")
                repo_result = repo_update(self.id, data)

            # Update the current instance with the result
            for key, value in repo_result[0].items():
                if hasattr(self, key):
                    setattr(self, key, value)

        except Exception as e:
            logger.error(f"Error saving {self.__class__.table_name}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(e)

    def _prepare_save_data(self) -> Dict[str, Any]:
        data = self.model_dump()
        logger.debug(f"Preparing data for save: {data}")
        del data["created"]
        del data["updated"]
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


class Notebook(ObjectModel):
    table_name: ClassVar[str] = "notebook"
    name: str
    description: str

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise InvalidInputError("Notebook name cannot be empty")
        return v

    @property
    def sources(self) -> List["Source"]:
        try:
            srcs = repo_query(f"""
                select * from (
                    select
                    <- source as source
                    from reference
                    where out={self.id}
                    fetch source
                )
                order by source.updated desc
            """)
            return [Source(**src["source"][0]) for src in srcs] if srcs else []
        except Exception as e:
            logger.error(f"Error fetching sources for notebook {self.id}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError("Failed to fetch sources for notebook")

    @property
    def notes(self) -> List["Note"]:
        try:
            srcs = repo_query(f"""
                select * from (
                    select
                    <- note as note
                    from artifact
                    where out={self.id}
                    fetch note
                )
                order by updated desc
            """)
            return [Note(**src["note"][0]) for src in srcs] if srcs else []
        except Exception as e:
            logger.error(f"Error fetching notes for notebook {self.id}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError("Failed to fetch notes for notebook")


class Asset(BaseModel):
    file_path: Optional[str] = None
    url: Optional[str] = None


class SourceInsight(ObjectModel):
    insight_type: str
    content: str


class Source(ObjectModel):
    table_name: ClassVar[str] = "source"
    asset: Optional[Asset] = None
    title: Optional[str] = None
    topics: Optional[List[str]] = Field(default_factory=list)
    full_text: Optional[str] = None

    def get_context(
        self, context_size: Literal["short", "long"] = "short"
    ) -> Dict[str, Any]:
        if context_size == "long":
            return dict(
                id=self.id,
                title=self.title,
                insights=self.insights,
                full_text=self.full_text,
            )
        else:
            return dict(id=self.id, title=self.title, insights=self.insights)

    @property
    def insights(self) -> List[SourceInsight]:
        try:
            result = repo_query(
                f"""
                SELECT * FROM source_insight WHERE source={self.id}
                """
            )
            return [SourceInsight(**insight) for insight in result]
        except Exception as e:
            logger.error(f"Error fetching insights for source {self.id}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError("Failed to fetch insights for source")

    def add_to_notebook(self, notebook_id: str) -> Any:
        if not notebook_id:
            raise InvalidInputError("Notebook ID must be provided")
        return self.relate("reference", notebook_id)

    def save_chunks(self, text: str) -> None:
        if not text:
            raise InvalidInputError("Text cannot be empty")
        try:
            chunks = split_text(text, chunk=500000, overlap=1000)
            logger.debug(f"Split into {len(chunks)} chunks")
            for i, chunk in enumerate(chunks):
                logger.debug(f"Saving chunk {i}")
                data = {"source": self.id, "order": i, "content": surreal_clean(chunk)}
                repo_create(
                    "source_chunk",
                    data,
                )
        except Exception as e:
            logger.exception(e)
            logger.error(f"Error saving chunks for source {self.id}: {str(e)}")
            raise DatabaseOperationError(e)

    def vectorize(self) -> None:
        try:
            full_text = self.full_text
            if not full_text:
                return
            chunks = split_text(
                self.full_text,
                chunk=int(os.environ.get("EMBEDDING_CHUNK_SIZE", 1000)),
                overlap=int(os.environ.get("EMBEDDING_CHUNK_OVERLAP", 1000)),
            )
            logger.debug(f"Split into {len(chunks)} chunks")

            # future: we can increase the batch size after surreal launches their new SDK
            for i, chunk in enumerate(chunks):
                repo_query(
                    f"""
                    CREATE source_embedding CONTENT {{
                            "source": {self.id},
                            "order": {i},
                            "content": $content,
                            "embedding": {get_embedding(chunk)},
                    }};""",
                    {"content": surreal_clean(chunk)},
                )
        except Exception as e:
            logger.error(f"Error vectorizing source {self.id}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(e)

    @classmethod
    def search(cls, query: str) -> List[Dict[str, Any]]:
        if not query:
            raise InvalidInputError("Search query cannot be empty")
        try:
            result = repo_query(
                """
                SELECT * omit full_text
                FROM source
                WHERE string::lowercase(title) CONTAINS $query or title @@ $query 
                OR string::lowercase(summary) CONTAINS $query or summary @@ $query 
                OR string::lowercase(full_text) CONTAINS $query or full_text @@ $query 
            """,
                {"query": query},
            )
            return result
        except Exception as e:
            logger.error(f"Error searching sources: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError("Failed to search sources")

    def add_insight(self, insight_type: str, content: str) -> Any:
        if not insight_type or not content:
            raise InvalidInputError("Insight type and content must be provided")
        try:
            embedding = get_embedding(content)
            return repo_query(
                f"""
                CREATE source_insight CONTENT {{
                        "source": {self.id},
                        "insight_type": '{insight_type}',
                        "content": $content,
                        "embedding": {embedding},
                }};""",
                {"content": surreal_clean(content)},
            )
        except Exception as e:
            logger.error(f"Error adding insight to source {self.id}: {str(e)}")
            raise DatabaseOperationError(e)

    def summarize(self) -> "Source":
        try:
            config = RunnableConfig(configurable=dict(thread_id=self.id))
            result = summarizer.invoke({"content": self.full_text}, config=config)[
                "output"
            ]
            self.add_insight("summary", surreal_clean(result.summary))
            self.title = surreal_clean(result.title)
            self.topics = result.topics
            self.save()
            return self
        except Exception as e:
            logger.error(f"Error summarizing source {self.id}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(e)


class Note(ObjectModel):
    table_name: ClassVar[str] = "note"
    title: Optional[str] = None
    note_type: Optional[Literal["human", "ai"]] = "human"
    content: Optional[str] = None

    @field_validator("content")
    @classmethod
    def content_must_not_be_empty(cls, v):
        if v is not None and not v.strip():
            raise InvalidInputError("Note content cannot be empty")
        return v

    def add_to_notebook(self, notebook_id: str) -> Any:
        if not notebook_id:
            raise InvalidInputError("Notebook ID must be provided")
        return self.relate("artifact", notebook_id)

    def get_context(
        self, context_size: Literal["short", "long"] = "short"
    ) -> Dict[str, Any]:
        if context_size == "long":
            return dict(id=self.id, title=self.title, content=self.content)
        else:
            return dict(
                id=self.id,
                title=self.title,
                content=self.content[:100] if self.content else None,
            )

    def needs_embedding(self) -> bool:
        return True

    def get_embedding_content(self) -> Optional[str]:
        return self.content


def text_search(
    keyword: str, results: int, source: bool = True, note: bool = True
) -> List[Dict[str, Any]]:
    if not keyword:
        raise InvalidInputError("Search keyword cannot be empty")
    try:
        results = repo_query(
            """
            SELECT * FROM fn::text_search($keyword, $results, $source, $note);
            """,
            {"keyword": keyword, "results": results, "source": source, "note": note},
        )
        return results
    except Exception as e:
        logger.error(f"Error performing text search: {str(e)}")
        logger.exception(e)
        raise DatabaseOperationError("Failed to perform text search")


def vector_search(
    keyword: str, results: int, source: bool = True, note: bool = True
) -> List[Dict[str, Any]]:
    if not keyword:
        raise InvalidInputError("Search keyword cannot be empty")
    try:
        results = repo_query(
            """
            SELECT * FROM fn::vector_search($keyword, $results, $source, $note);
            """,
            {"keyword": keyword, "results": results, "source": source, "note": note},
        )
        return results
    except Exception as e:
        logger.error(f"Error performing vector search: {str(e)}")
        logger.exception(e)
        raise DatabaseOperationError("Failed to perform vector search")
