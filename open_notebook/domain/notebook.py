from typing import Any, ClassVar, Dict, List, Literal, Optional

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
        EMBEDDING_MODEL = model_manager.embedding_model

        try:
            if not self.full_text:
                return
            chunks = split_text(
                self.full_text,
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

    # @classmethod
    # def search(cls, query: str) -> List[Dict[str, Any]]:
    #     if not query:
    #         raise InvalidInputError("Search query cannot be empty")
    #     try:
    #         result = repo_query(
    #             """
    #             SELECT * omit full_text
    #             FROM source
    #             WHERE string::lowercase(title) CONTAINS $query or title @@ $query
    #             OR string::lowercase(summary) CONTAINS $query or summary @@ $query
    #             OR string::lowercase(full_text) CONTAINS $query or full_text @@ $query
    #         """,
    #             {"query": query},
    #         )
    #         return result
    #     except Exception as e:
    #         logger.error(f"Error searching sources: {str(e)}")
    #         logger.exception(e)
    #         raise DatabaseOperationError("Failed to search sources")

    def add_insight(self, insight_type: str, content: str) -> Any:
        EMBEDDING_MODEL = model_manager.embedding_model

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
            SELECT * FROM fn::text_search($keyword, $results, $source, $note);
            """,
            {"keyword": keyword, "results": results, "source": source, "note": note},
        )
        return results
    except Exception as e:
        logger.error(f"Error performing text search: {str(e)}")
        logger.exception(e)
        raise DatabaseOperationError(e)


def vector_search(keyword: str, results: int, source: bool = True, note: bool = True):
    if not keyword:
        raise InvalidInputError("Search keyword cannot be empty")
    try:
        EMBEDDING_MODEL = model_manager.embedding_model
        embed = EMBEDDING_MODEL.embed(keyword)
        results = repo_query(
            """
            SELECT * FROM fn::vector_search($embed, $results, $source, $note, 0.15);
            """,
            {"embed": embed, "results": results, "source": source, "note": note},
        )
        return results
    except Exception as e:
        logger.error(f"Error performing vector search: {str(e)}")
        logger.exception(e)
        raise DatabaseOperationError(e)


def hybrid_search(
    keyword_search: List[str],
    embed_search: List[str],
    results: int = 50,
    source: bool = True,
    note: bool = True,
    max_chunks_per_doc: int = 3,
    min_results_per_query: int = 3,
) -> Dict[str, List[Dict]]:
    if not keyword_search and not embed_search:
        raise InvalidInputError("At least one search term required")

    # Process keyword searches
    all_keyword_results = {}  # Dictionary to store results per keyword
    for keyword in keyword_search:
        try:
            search_results = text_search(keyword, results, source, note)
            # Sort results by relevance
            sorted_results = sorted(
                search_results, key=lambda x: x.get("relevance", 0), reverse=True
            )
            # Group by parent_id and limit chunks per document
            seen_parent_ids = {}
            filtered_results = []
            for result in sorted_results:
                parent_id = result["parent_id"]
                if parent_id not in seen_parent_ids:
                    seen_parent_ids[parent_id] = 1
                    filtered_results.append(result)
                elif seen_parent_ids[parent_id] < max_chunks_per_doc:
                    seen_parent_ids[parent_id] += 1
                    filtered_results.append(result)
            all_keyword_results[keyword] = filtered_results
        except Exception as e:
            logger.warning(f"Error in keyword search for term '{keyword}': {str(e)}")
            continue

    # Ensure minimum results from each keyword query
    keyword_results = []
    remaining_slots = results

    # First pass: add minimum results from each query
    for keyword, query_results in all_keyword_results.items():
        keyword_results.extend(query_results[:min_results_per_query])
        remaining_slots -= min(len(query_results), min_results_per_query)

    # Second pass: fill remaining slots with best results
    all_remaining = []
    for keyword, query_results in all_keyword_results.items():
        all_remaining.extend(query_results[min_results_per_query:])

    # Sort remaining by relevance and add until we hit the limit
    all_remaining = sorted(
        all_remaining, key=lambda x: x.get("relevance", 0), reverse=True
    )
    seen_ids = {r["id"] for r in keyword_results}
    for result in all_remaining:
        if remaining_slots <= 0:
            break
        if result["id"] not in seen_ids:
            keyword_results.append(result)
            seen_ids.add(result["id"])
            remaining_slots -= 1

    # Process vector searches with the same approach
    all_vector_results = {}  # Dictionary to store results per embedding
    for embed in embed_search:
        try:
            search_results = vector_search(embed, results, source, note)
            # Sort results by similarity
            sorted_results = sorted(
                search_results, key=lambda x: x.get("similarity", 0), reverse=True
            )
            # Group by parent_id and limit chunks per document
            seen_parent_ids = {}
            filtered_results = []
            for result in sorted_results:
                parent_id = result["parent_id"]
                if parent_id not in seen_parent_ids:
                    seen_parent_ids[parent_id] = 1
                    filtered_results.append(result)
                elif seen_parent_ids[parent_id] < max_chunks_per_doc:
                    seen_parent_ids[parent_id] += 1
                    filtered_results.append(result)
            all_vector_results[embed] = filtered_results
        except Exception as e:
            logger.warning(f"Error in vector search for term '{embed}': {str(e)}")
            continue

    # Ensure minimum results from each vector query
    vector_results = []
    remaining_slots = results

    # First pass: add minimum results from each query
    for embed, query_results in all_vector_results.items():
        vector_results.extend(query_results[:min_results_per_query])
        remaining_slots -= min(len(query_results), min_results_per_query)

    # Second pass: fill remaining slots with best results
    all_remaining = []
    for embed, query_results in all_vector_results.items():
        all_remaining.extend(query_results[min_results_per_query:])

    # Sort remaining by similarity and add until we hit the limit
    all_remaining = sorted(
        all_remaining, key=lambda x: x.get("similarity", 0), reverse=True
    )
    seen_ids = {r["id"] for r in vector_results}
    for result in all_remaining:
        if remaining_slots <= 0:
            break
        if result["id"] not in seen_ids:
            vector_results.append(result)
            seen_ids.add(result["id"])
            remaining_slots -= 1

    return {"keyword_results": keyword_results, "vector_results": vector_results}
