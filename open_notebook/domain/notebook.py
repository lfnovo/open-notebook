import os
from typing import Any, ClassVar, Dict, List, Literal, Optional

from langchain_core.runnables.config import RunnableConfig
from loguru import logger
from pydantic import BaseModel, Field, field_validator

from open_notebook.config import EMBEDDING_MODEL
from open_notebook.domain.base import ObjectModel
from open_notebook.exceptions import (
    DatabaseOperationError,
    InvalidInputError,
)
from open_notebook.graphs.multipattern import graph as pattern_graph
from open_notebook.graphs.recursive_toc import graph as toc_graph
from open_notebook.repository import (
    repo_create,
    repo_query,
)
from open_notebook.utils import split_text, surreal_clean


class Notebook(ObjectModel):
    table_name: ClassVar[str] = "notebook"
    name: str
    description: str
    archived: Optional[bool] = False

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
                select * OMIT full_text from (
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
            raise DatabaseOperationError(e)

    @property
    def notes(self) -> List["Note"]:
        try:
            srcs = repo_query(f"""
                select * OMIT content from (
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
            raise DatabaseOperationError(e)


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
            if not self.full_text:
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
                            "embedding": {EMBEDDING_MODEL.embed(chunk)},
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
            embedding = EMBEDDING_MODEL.embed(content)
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

    # todo: move this to content processing pipeline as a major graph
    def generate_toc_and_title(self) -> "Source":
        try:
            config = RunnableConfig(configurable=dict(thread_id=self.id))
            result = toc_graph.invoke({"content": self.full_text}, config=config)
            self.add_insight("Table of Contents", surreal_clean(result["toc"]))
            if not self.title:
                transformations = [
                    "Based on the Table of Contents below, please provide a Title for this content, with max 15 words"
                ]
                output = pattern_graph.invoke(
                    dict(content_stack=[result["toc"]], transformations=transformations)
                )
                self.title = surreal_clean(output["output"])
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


def text_search(keyword: str, results: int, source: bool = True, note: bool = True):
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


def vector_search(keyword: str, results: int, source: bool = True, note: bool = True):
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
