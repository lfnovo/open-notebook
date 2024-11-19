from concurrent.futures import ThreadPoolExecutor
from typing import Any, ClassVar, Dict, List, Literal, Optional, Tuple

from loguru import logger
from pydantic import BaseModel, Field, field_validator

from open_notebook.database.repository import (
    repo_query,
)
from open_notebook.domain.base import ObjectModel
from open_notebook.domain.models import model_manager
from open_notebook.exceptions import (
    DatabaseOperationError,
    InvalidInputError,
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
                select * omit source.full_text from (
                select in as source from reference where out={self.id}
                fetch source
            ) order by source.updated desc
            """)
            return [Source(**src["source"]) for src in srcs] if srcs else []
        except Exception as e:
            logger.error(f"Error fetching sources for notebook {self.id}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(e)

    @property
    def notes(self) -> List["Note"]:
        try:
            srcs = repo_query(f"""
            select * omit note.content, note.embedding from (
                select in as note from artifact where out={self.id}
                fetch note
            ) order by note.updated desc
            """)
            return [Note(**src["note"]) for src in srcs] if srcs else []
        except Exception as e:
            logger.error(f"Error fetching notes for notebook {self.id}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(e)

    @property
    def chat_sessions(self) -> List["ChatSession"]:
        try:
            srcs = repo_query(f"""
                select * from (
                    select
                    <- chat_session as chat_session
                    from refers_to
                    where out={self.id}
                    fetch chat_session
                )
                order by chat_session.updated desc
            """)
            return (
                [ChatSession(**src["chat_session"][0]) for src in srcs] if srcs else []
            )
        except Exception as e:
            logger.error(f"Error fetching notes for notebook {self.id}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(e)


class Asset(BaseModel):
    file_path: Optional[str] = None
    url: Optional[str] = None


class SourceEmbedding(ObjectModel):
    table_name: ClassVar[str] = "source_embedding"
    content: str

    @property
    def source(self) -> "Source":
        try:
            src = repo_query(f"""
            select source.* from {self.id}                    fetch source

            """)
            return Source(**src[0]["source"])
        except Exception as e:
            logger.error(f"Error fetching source for embedding {self.id}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(e)


class SourceInsight(ObjectModel):
    table_name: ClassVar[str] = "source_insight"
    insight_type: str
    content: str

    @property
    def source(self) -> "Source":
        try:
            src = repo_query(f"""
            select source.* from {self.id}                    fetch source

            """)
            return Source(**src[0]["source"])
        except Exception as e:
            logger.error(f"Error fetching source for insight {self.id}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(e)

    def save_as_note(self, notebook_id: str = None) -> Any:
        note = Note(
            title=f"{self.insight_type} from source {self.source.title}",
            content=self.content,
        )
        note.save()
        if notebook_id:
            note.add_to_notebook(notebook_id)
        return note


class Source(ObjectModel):
    table_name: ClassVar[str] = "source"
    asset: Optional[Asset] = None
    title: Optional[str] = None
    topics: Optional[List[str]] = Field(default_factory=list)
    full_text: Optional[str] = None

    def get_context(
        self, context_size: Literal["short", "long"] = "short"
    ) -> Dict[str, Any]:
        insights = [insight.model_dump() for insight in self.insights]
        if context_size == "long":
            return dict(
                id=self.id,
                title=self.title,
                insights=insights,
                full_text=self.full_text,
            )
        else:
            return dict(id=self.id, title=self.title, insights=insights)

    @property
    def embedded_chunks(self) -> int:
        try:
            result = repo_query(
                f"""
                select count() as chunks from source_embedding where source={self.id} GROUP ALL
                """
            )
            if len(result) == 0:
                return 0
            return result[0]["chunks"]
        except Exception as e:
            logger.error(f"Error fetching insights for source {self.id}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(f"Failed to count chunks for source: {str(e)}")

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

    def vectorize(self) -> None:
        logger.info(f"Starting vectorization for source {self.id}")
        EMBEDDING_MODEL = model_manager.embedding_model

        try:
            if not self.full_text:
                logger.warning(f"No text to vectorize for source {self.id}")
                return

            chunks = split_text(
                self.full_text,
            )
            chunk_count = len(chunks)
            logger.info(f"Split into {chunk_count} chunks for source {self.id}")

            if chunk_count == 0:
                logger.warning("No chunks created after splitting")
                return

            def process_chunk(args: Tuple[int, str]) -> Tuple[int, List[float], str]:
                idx, chunk = args
                logger.debug(f"Processing chunk {idx}/{chunk_count}")
                try:
                    embedding = EMBEDDING_MODEL.embed(chunk)
                    cleaned_content = surreal_clean(chunk)
                    logger.debug(f"Successfully processed chunk {idx}")
                    return (idx, embedding, cleaned_content)
                except Exception as e:
                    logger.error(f"Error processing chunk {idx}: {str(e)}")
                    raise

            # Process chunks in parallel while preserving order
            logger.info("Starting parallel processing of chunks")
            with ThreadPoolExecutor(max_workers=8) as executor:
                # Create list of (index, chunk) tuples
                chunk_tasks = list(enumerate(chunks))
                # Process all chunks in parallel and get results
                results = list(executor.map(process_chunk, chunk_tasks))

            logger.info(f"Parallel processing complete. Got {len(results)} results")

            # Insert results in order (they're already ordered by index)
            for idx, embedding, content in results:
                logger.debug(f"Inserting chunk {idx} into database")
                repo_query(
                    f"""
                    CREATE source_embedding CONTENT {{
                            "source": {self.id},
                            "order": {idx},
                            "content": $content,
                            "embedding": {embedding},
                    }};""",
                    {"content": content},
                )

            logger.info(f"Vectorization complete for source {self.id}")

        except Exception as e:
            logger.error(f"Error vectorizing source {self.id}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(e)

    def add_insight(self, insight_type: str, content: str) -> Any:
        EMBEDDING_MODEL = model_manager.embedding_model
        if not EMBEDDING_MODEL:
            logger.warning("No embedding model found. Insight will not be searchable.")

        if not insight_type or not content:
            raise InvalidInputError("Insight type and content must be provided")
        try:
            embedding = EMBEDDING_MODEL.embed(content) if EMBEDDING_MODEL else []
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
            raise  # DatabaseOperationError(e)


class Note(ObjectModel):
    table_name: ClassVar[str] = "note"
    title: Optional[str] = None
    note_type: Optional[Literal["human", "ai"]] = None
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


class ChatSession(ObjectModel):
    table_name: ClassVar[str] = "chat_session"
    title: Optional[str] = None

    def relate_to_notebook(self, notebook_id: str) -> Any:
        if not notebook_id:
            raise InvalidInputError("Notebook ID must be provided")
        return self.relate("refers_to", notebook_id)


def text_search(keyword: str, results: int, source: bool = True, note: bool = True):
    if not keyword:
        raise InvalidInputError("Search keyword cannot be empty")
    try:
        results = repo_query(
            """
            select *
            from fn::text_search($keyword, $results, $source, $note)
            """,
            {"keyword": keyword, "results": results, "source": source, "note": note},
        )
        return results
    except Exception as e:
        logger.error(f"Error performing text search: {str(e)}")
        logger.exception(e)
        raise DatabaseOperationError(e)


def vector_search(
    keyword: str,
    results: int,
    source: bool = True,
    note: bool = True,
    minimum_score=0.2,
):
    if not keyword:
        raise InvalidInputError("Search keyword cannot be empty")
    try:
        EMBEDDING_MODEL = model_manager.embedding_model
        embed = EMBEDDING_MODEL.embed(keyword)
        results = repo_query(
            """
            SELECT * FROM fn::vector_search($embed, $results, $source, $note, $minimum_score);
            """,
            {
                "embed": embed,
                "results": results,
                "source": source,
                "note": note,
                "minimum_score": minimum_score,
            },
        )
        return results
    except Exception as e:
        logger.error(f"Error performing vector search: {str(e)}")
        logger.exception(e)
        raise DatabaseOperationError(e)
