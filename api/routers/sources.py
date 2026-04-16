import asyncio
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

import spacy

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse, Response
from loguru import logger
from surreal_commands import execute_command_sync, submit_command

from api.command_service import CommandService
from api.models import (
    AssetModel,
    CommonGraphCreate,
    CommonGraphResponse,
    CreateSourceInsightRequest,
    InsightCreationResponse,
    SourceCreate,
    SourceInsightResponse,
    SourceListResponse,
    SourceResponse,
    SourceStatusResponse,
    SourceUpdate,
)
from commands.source_commands import SourceProcessingInput
from open_notebook.config import UPLOADS_FOLDER
from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.common_graph import CommonGraph
from open_notebook.domain.notebook import Notebook, Source
from open_notebook.domain.transformation import Transformation
from open_notebook.exceptions import InvalidInputError, NotFoundError
from urllib.parse import unquote
from pydantic import BaseModel

router = APIRouter()


def generate_unique_filename(original_filename: str, upload_folder: str) -> str:
    """Generate unique filename like Streamlit app (append counter if file exists)."""
    file_path = Path(upload_folder)
    file_path.mkdir(parents=True, exist_ok=True)

    # Split filename and extension
    stem = Path(original_filename).stem
    suffix = Path(original_filename).suffix

    # Check if file exists and generate unique name
    counter = 0
    while True:
        if counter == 0:
            new_filename = original_filename
        else:
            new_filename = f"{stem} ({counter}){suffix}"

        full_path = file_path / new_filename
        if not full_path.exists():
            return str(full_path)
        counter += 1


async def save_uploaded_file(upload_file: UploadFile) -> str:
    """Save uploaded file to uploads folder and return file path."""
    if not upload_file.filename:
        raise ValueError("No filename provided")

    # Generate unique filename
    file_path = generate_unique_filename(upload_file.filename, UPLOADS_FOLDER)

    try:
        # Save file
        with open(file_path, "wb") as f:
            content = await upload_file.read()
            f.write(content)

        logger.info(f"Saved uploaded file to: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        # Clean up partial file if it exists
        if os.path.exists(file_path):
            os.unlink(file_path)
        raise


def parse_source_form_data(
    type: str = Form(...),
    notebook_id: Optional[str] = Form(None),
    notebooks: Optional[str] = Form(None),  # JSON string of notebook IDs
    url: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    transformations: Optional[str] = Form(None),  # JSON string of transformation IDs
    embed: str = Form("false"),  # Accept as string, convert to bool
    delete_source: str = Form("false"),  # Accept as string, convert to bool
    async_processing: str = Form("false"),  # Accept as string, convert to bool
    file: Optional[UploadFile] = File(None),
) -> tuple[SourceCreate, Optional[UploadFile]]:
    """Parse form data into SourceCreate model and return upload file separately."""
    import json

    # Convert string booleans to actual booleans
    def str_to_bool(value: str) -> bool:
        return value.lower() in ("true", "1", "yes", "on")

    embed_bool = str_to_bool(embed)
    delete_source_bool = str_to_bool(delete_source)
    async_processing_bool = str_to_bool(async_processing)

    # Parse JSON strings
    notebooks_list = None
    if notebooks:
        try:
            notebooks_list = json.loads(notebooks)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in notebooks field: {notebooks}")
            raise ValueError("Invalid JSON in notebooks field")

    transformations_list = []
    if transformations:
        try:
            transformations_list = json.loads(transformations)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in transformations field: {transformations}")
            raise ValueError("Invalid JSON in transformations field")

    # Create SourceCreate instance
    try:
        source_data = SourceCreate(
            type=type,
            notebook_id=notebook_id,
            notebooks=notebooks_list,
            url=url,
            content=content,
            title=title,
            file_path=None,  # Will be set later if file is uploaded
            transformations=transformations_list,
            embed=embed_bool,
            delete_source=delete_source_bool,
            async_processing=async_processing_bool,
        )
        pass  # SourceCreate instance created successfully
    except Exception as e:
        logger.error(f"Failed to create SourceCreate instance: {e}")
        raise

    return source_data, file


COMMON_GRAPH_BLOCKLIST = {
    'said', 'told', 'asked', 'went', 'came', 'met', 'along', 'namely',
    'thereafter', 'stayed', 'rented', 'months', 'case', 'near', 'brother',
    'associates', 'car', 'village', 'person', 'people', 'man', 'men',
    'woman', 'women', 'one', 'another', 'other', 'some', 'many', 'most',
    'few', 'first', 'last', 'next', 'time', 'times', 'day', 'days', 'year',
    'years', 'back', 'good', 'new', 'still', 'really', 'very',
    'may', 'might', 'shall', 'should', 'would', 'could', 'need', 'needed',
    'needs', 'want', 'wanted', 'wants', 'get', 'gets', 'got', 'make', 'makes',
    'made', 'take', 'takes', 'took', 'taken', 'say', 'says', 'go', 'goes',
    'gone', 'see', 'sees', 'saw', 'seen', 'know', 'knows', 'knew', 'known',
    'think', 'thinks', 'thought', 'feel', 'feels', 'felt', 'look', 'looks',
    'looked', 'help', 'helps', 'helped', 'show', 'shows', 'showed', 'shown',
}

_spacy_nlp: Optional[spacy.language.Language] = None


def _get_spacy_nlp() -> Optional[spacy.language.Language]:
    global _spacy_nlp
    if _spacy_nlp is not None:
        return _spacy_nlp

    try:
        _spacy_nlp = spacy.load("en_core_web_sm")
        return _spacy_nlp
    except OSError:
        logger.warning(
            "spaCy model 'en_core_web_sm' is missing. "
            "Falling back to regex-based term extraction. "
            "Install it with: python -m spacy download en_core_web_sm"
        )
        return None


def _extract_terms_fallback(text: str) -> Counter[str]:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    tokens = [token for token in cleaned.split() if len(token) > 2 and token not in COMMON_GRAPH_BLOCKLIST]
    return Counter(tokens)


def _extract_terms(text: str) -> Counter[str]:
    if not text:
        return Counter()

    nlp_model = _get_spacy_nlp()
    if nlp_model is None:
        return _extract_terms_fallback(text)

    doc = nlp_model(text)
    term_freq: Counter[str] = Counter()

    for ent in doc.ents:
        if ent.label_ in {"PERSON", "GPE", "LOC", "ORG"}:
            term = ent.text.lower().strip()
            if len(term) > 2 and term not in COMMON_GRAPH_BLOCKLIST:
                term_freq[term] += 3

    for chunk in doc.noun_chunks:
        term = chunk.root.lemma_.lower().strip()
        if (
            len(term) > 2
            and not chunk.root.is_stop
            and term not in COMMON_GRAPH_BLOCKLIST
            and not term.isnumeric()
        ):
            term_freq[term] += 1

    return term_freq


def _build_common_graph_metadata(sources: List[Source]) -> Dict[str, Any]:
    term_counters = []
    source_ids = []
    for source in sources:
        text = source.full_text or source.title or ''
        term_counters.append(_extract_terms(text))
        source_ids.append(source.id or '')

    if not term_counters:
        return {}

    common_terms = set(term_counters[0].keys())
    for counter in term_counters[1:]:
        common_terms &= set(counter.keys())

    nodes: List[Dict[str, Any]] = []
    links: List[Dict[str, Any]] = []

    for idx, source in enumerate(sources):
        nodes.append(
            {
                'id': f'source:{idx}',
                'label': source.title or source.id or f'Source {idx + 1}',
                'type': 'source',
                'source_id': source.id,
            }
        )

    if not common_terms:
        return {
            'common_terms': [],
            'graph': {'nodes': nodes, 'links': []},
        }

    term_scores = {
        term: sum(counter[term] for counter in term_counters)
        for term in common_terms
    }
    selected_terms = sorted(term_scores.items(), key=lambda item: item[1], reverse=True)[:15]

    for term, score in selected_terms:
        term_id = f'term:{term}'
        nodes.append(
            {
                'id': term_id,
                'label': term,
                'type': 'term',
                'weight': score,
            }
        )
        for source_idx, counter in enumerate(term_counters):
            if counter[term] > 0:
                links.append(
                    {
                        'source': f'source:{source_idx}',
                        'target': term_id,
                        'weight': counter[term],
                    }
                )

    return {
        'common_terms': [term for term, _ in selected_terms],
        'graph': {'nodes': nodes, 'links': links},
    }


# Per-document extraction prompt — used in step 1
PER_DOC_EXTRACT_PROMPT = (
    "You are an expert entity extraction system for investigative documents.\n"
    "Extract ALL important entities from the document below.\n"
    "Focus on:\n"
    "- People (full names of individuals)\n"
    "- Places (cities, villages, addresses, districts)\n"
    "- Organizations (police units, companies, groups)\n"
    "- Key activities or events (crimes, arrests, meetings, transactions)\n"
    "- Significant objects (vehicles, weapons, items)\n"
    "Rules:\n"
    "- Keep labels concise (1-4 words).\n"
    "- Use proper names, not pronouns.\n"
    "- Maximum 25 items.\n"
    "Return ONLY a valid JSON array of strings. No explanation.\n"
    "Example: [\"Ankit Kumar\", \"Delhi\", \"arms smuggling\", \"blue Honda\"]"
)

# Default prompt used when user provides custom prompt with {{documents_input}}
DEFAULT_COMMON_GRAPH_PROMPT = (
    "You are an expert entity and activity extraction system designed to build a "
    "\"Common Graph\" from one or more documents.\n"
    "Input: You will receive one or multiple documents.\n"
    "Your task: Extract the most important and relevant elements across ALL documents combined.\n"
    "Focus ONLY on:\n"
    "- People (individual names)\n"
    "- Places (cities, locations, addresses)\n"
    "- Organizations (companies, institutions, groups)\n"
    "- Key activities or events (crimes, meetings, transactions, incidents)\n"
    "- Significant objects (vehicles, weapons, important items)\n"
    "Instructions:\n"
    "- Analyze ALL documents together as a single dataset.\n"
    "- Merge duplicate or similar entities.\n"
    "- Prioritize entities/events that appear frequently or are important.\n"
    "- Include both common entities and critical unique entities.\n"
    "- Keep labels concise (1 to 4 words max).\n"
    "- Avoid vague terms.\n"
    "- Do not repeat items.\n"
    "- Maximum 20 items total.\n"
    "Output Format:\n"
    "- Return ONLY a valid JSON array of strings.\n"
    "- No explanations, no extra text.\n"
    "Example Output: [\"John Smith\", \"New York City\", \"financial fraud\"]\n"
    "Now process the following documents:\n"
    "{{documents_input}}"
)


async def _extract_entities_per_doc(source, model_id, re_mod, json_mod, provision_fn, SystemMessage, HumanMessage):
    """Extract entities from a single document using LLM."""
    text = source.full_text or source.title or ''
    if not text.strip():
        return []
    truncated = text[:4000]
    try:
        payload = [
            SystemMessage(content=PER_DOC_EXTRACT_PROMPT),
            HumanMessage(content=truncated),
        ]
        chain = await provision_fn(str(payload), model_id, "transformation", max_tokens=512)
        response = await chain.ainvoke(payload)
        raw = str(response.content if hasattr(response, 'content') else response).strip()
        if '```' in raw:
            raw = re_mod.sub(r'```(?:json)?\s*', '', raw).strip()
        a, b = raw.find('['), raw.rfind(']')
        if a != -1 and b != -1:
            parsed = json_mod.loads(raw[a:b+1])
            return [str(e).strip() for e in parsed if e and len(str(e).strip()) > 1]
    except Exception as ex:
        logger.warning(f"[CommonGraph] Per-doc extraction failed: {ex}")
    return []


def _normalize(s):
    """Lowercase + strip for comparison."""
    return s.lower().strip()


async def _build_common_graph_metadata_llm(
    sources,
    model_id,
    prompt=None,
):
    """
    Two-step extraction:
    1. Extract entities per document
    2. Find common entities (appear in 2+ docs) + important unique ones
    3. Build graph with source nodes + entity nodes, colored by which docs mention them
    """
    from langchain_core.messages import HumanMessage, SystemMessage
    from open_notebook.ai.provision import provision_langchain_model
    import json as _json
    import re as _re

    # If user provided a custom prompt with {{documents_input}}, use single-pass mode
    base_prompt = prompt or DEFAULT_COMMON_GRAPH_PROMPT
    use_custom_prompt = prompt is not None and '{{documents_input}}' in base_prompt

    if use_custom_prompt:
        # Single-pass: user's custom prompt
        combined_parts = []
        for idx, source in enumerate(sources):
            text = source.full_text or source.title or ''
            combined_parts.append(
                f"--- Document {idx + 1}: {source.title or f'Source {idx + 1}'} ---\n{text[:3500]}"
            )
        documents_input = "\n\n".join(combined_parts)
        final_prompt = base_prompt.replace('{{documents_input}}', documents_input)
        system_msg = "You are an expert entity extraction system. Return ONLY a valid JSON array of strings."
        user_msg = final_prompt

        entities_all = []
        try:
            payload = [SystemMessage(content=system_msg), HumanMessage(content=user_msg)]
            chain = await provision_langchain_model(str(payload), model_id, "transformation", max_tokens=1024)
            response = await chain.ainvoke(payload)
            raw = str(response.content if hasattr(response, 'content') else response).strip()
            logger.info(f"[CommonGraph] Custom prompt response: {raw[:400]}")
            if '```' in raw:
                raw = _re.sub(r'```(?:json)?\s*', '', raw).strip()
            a, b = raw.find('['), raw.rfind(']')
            if a != -1 and b != -1:
                parsed = _json.loads(raw[a:b+1])
                entities_all = [str(e).strip() for e in parsed if e and len(str(e).strip()) > 1]
        except Exception as e:
            logger.warning(f"[CommonGraph] Custom prompt failed: {e}, falling back to NLP")
            return _build_common_graph_metadata(sources)

        if not entities_all:
            return _build_common_graph_metadata(sources)

        # For custom prompt, check which sources mention each entity
        nodes, links = [], []
        for idx, source in enumerate(sources):
            nodes.append({'id': f'source:{idx}', 'label': source.title or f'Source {idx+1}', 'type': 'source', 'source_id': source.id})

        for i, entity in enumerate(entities_all[:20]):
            eid = f'entity:{i}'
            el = entity.lower()
            matches = [idx for idx, s in enumerate(sources) if el in (s.full_text or s.title or '').lower()]
            if not matches:
                matches = list(range(len(sources)))
            nodes.append({'id': eid, 'label': entity, 'type': 'entity', 'weight': len(matches), 'common': len(matches) > 1})
            for src_idx in matches:
                links.append({'source': f'source:{src_idx}', 'target': eid, 'type': 'mentions', 'weight': 1})

        return {'common_terms': entities_all[:20], 'graph': {'nodes': nodes, 'links': links}, 'graph_type': 'flat'}

    # ── TWO-STEP MODE (default) ──────────────────────────────────────────────
    # Step 1: Extract entities per document
    per_doc_entities = []
    for source in sources:
        entities = await _extract_entities_per_doc(
            source, model_id, _re, _json, provision_langchain_model, SystemMessage, HumanMessage
        )
        per_doc_entities.append(entities)
        logger.info(f"[CommonGraph] Doc '{source.title}': {len(entities)} entities: {entities[:8]}")

    if not any(per_doc_entities):
        logger.warning("[CommonGraph] No entities extracted from any doc, falling back to NLP")
        return _build_common_graph_metadata(sources)

    # Step 2: Find common entities (appear in 2+ docs) using normalized comparison
    # Build a map: normalized_label -> {canonical_label, doc_indices}
    entity_map: dict = {}
    for doc_idx, entities in enumerate(per_doc_entities):
        for entity in entities:
            norm = _normalize(entity)
            if norm not in entity_map:
                entity_map[norm] = {'label': entity, 'doc_indices': set(), 'count': 0}
            entity_map[norm]['doc_indices'].add(doc_idx)
            entity_map[norm]['count'] += 1

    # Separate common (2+ docs) from unique (1 doc)
    common_entities = {k: v for k, v in entity_map.items() if len(v['doc_indices']) >= 2}
    unique_entities = {k: v for k, v in entity_map.items() if len(v['doc_indices']) == 1}

    logger.info(f"[CommonGraph] Common entities ({len(common_entities)}): {list(common_entities.keys())[:10]}")
    logger.info(f"[CommonGraph] Unique entities ({len(unique_entities)}): {list(unique_entities.keys())[:5]}")

    # Sort common by doc coverage (most common first), then by count
    sorted_common = sorted(common_entities.values(), key=lambda x: (-len(x['doc_indices']), -x['count']))
    # Sort unique by count (most frequent first), take top ones
    sorted_unique = sorted(unique_entities.values(), key=lambda x: -x['count'])

    # Build final entity list: all common + top unique to fill up to 25
    final_entities = sorted_common[:20]
    remaining_slots = max(0, 25 - len(final_entities))
    final_entities += sorted_unique[:remaining_slots]

    if not final_entities:
        return _build_common_graph_metadata(sources)

    # Step 3: Build graph
    nodes, links = [], []

    for idx, source in enumerate(sources):
        nodes.append({
            'id': f'source:{idx}',
            'label': source.title or f'Source {idx+1}',
            'type': 'source',
            'source_id': source.id,
        })

    for i, ent in enumerate(final_entities):
        eid = f'entity:{i}'
        doc_indices = sorted(ent['doc_indices'])
        is_common = len(doc_indices) >= 2
        nodes.append({
            'id': eid,
            'label': ent['label'],
            'type': 'entity',
            'weight': len(doc_indices),
            'common': is_common,
        })
        for src_idx in doc_indices:
            links.append({
                'source': f'source:{src_idx}',
                'target': eid,
                'type': 'mentions',
                'weight': 1,
            })

    common_terms = [e['label'] for e in final_entities]
    logger.info(f"[CommonGraph] Final graph: {len(nodes)} nodes, {len(links)} links")

    return {
        'common_terms': common_terms,
        'graph': {'nodes': nodes, 'links': links},
        'graph_type': 'flat',
        'common_count': len(sorted_common),
        'unique_count': len(final_entities) - len(sorted_common),
    }


@router.get("/sources", response_model=List[SourceListResponse])
async def get_sources(
    notebook_id: Optional[str] = Query(None, description="Filter by notebook ID"),
    limit: int = Query(
        50, ge=1, le=100, description="Number of sources to return (1-100)"
    ),
    offset: int = Query(0, ge=0, description="Number of sources to skip"),
    sort_by: str = Query(
        "updated", description="Field to sort by (created or updated)"
    ),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
):
    """Get sources with pagination and sorting support."""
    try:
        # Validate sort parameters
        if sort_by not in ["created", "updated"]:
            raise HTTPException(
                status_code=400, detail="sort_by must be 'created' or 'updated'"
            )
        if sort_order.lower() not in ["asc", "desc"]:
            raise HTTPException(
                status_code=400, detail="sort_order must be 'asc' or 'desc'"
            )

        # Build ORDER BY clause
        order_clause = f"ORDER BY {sort_by} {sort_order.upper()}"

        # Build the query
        if notebook_id:
            # Verify notebook exists first
            notebook = await Notebook.get(notebook_id)
            if not notebook:
                raise HTTPException(status_code=404, detail="Notebook not found")

            # Query sources for specific notebook - include command field with FETCH
            query = f"""
                SELECT id, asset, created, title, updated, topics, command,
                (SELECT VALUE count() FROM source_insight WHERE source = $parent.id GROUP ALL)[0].count OR 0 AS insights_count,
                (SELECT VALUE id FROM source_embedding WHERE source = $parent.id LIMIT 1) != [] AS embedded
                FROM (select value in from reference where out=$notebook_id)
                {order_clause}
                LIMIT $limit START $offset
                FETCH command
            """
            result = await repo_query(
                query,
                {
                    "notebook_id": ensure_record_id(notebook_id),
                    "limit": limit,
                    "offset": offset,
                },
            )
        else:
            # Query all sources - include command field with FETCH
            query = f"""
                SELECT id, asset, created, title, updated, topics, command,
                (SELECT VALUE count() FROM source_insight WHERE source = $parent.id GROUP ALL)[0].count OR 0 AS insights_count,
                (SELECT VALUE id FROM source_embedding WHERE source = $parent.id LIMIT 1) != [] AS embedded
                FROM source
                {order_clause}
                LIMIT $limit START $offset
                FETCH command
            """
            result = await repo_query(query, {"limit": limit, "offset": offset})

        # Convert result to response model
        # Command data is already fetched via FETCH command clause
        response_list = []
        for row in result:
            command = row.get("command")
            command_id = None
            status = None
            processing_info = None

            # Extract status from fetched command object (already resolved by FETCH)
            if command and isinstance(command, dict):
                command_id = str(command.get("id")) if command.get("id") else None
                status = command.get("status")
                # Extract execution metadata from nested result structure
                result_data = command.get("result")
                execution_metadata = (
                    result_data.get("execution_metadata", {})
                    if isinstance(result_data, dict)
                    else {}
                )
                processing_info = {
                    "started_at": execution_metadata.get("started_at"),
                    "completed_at": execution_metadata.get("completed_at"),
                    "error": command.get("error_message"),
                }
            elif command:
                # Command exists but FETCH failed to resolve it (broken reference)
                command_id = str(command)
                status = "unknown"

            response_list.append(
                SourceListResponse(
                    id=row["id"],
                    title=row.get("title"),
                    topics=row.get("topics") or [],
                    asset=AssetModel(
                        file_path=row["asset"].get("file_path")
                        if row.get("asset")
                        else None,
                        url=row["asset"].get("url") if row.get("asset") else None,
                    )
                    if row.get("asset")
                    else None,
                    embedded=row.get("embedded", False),
                    embedded_chunks=0,  # Not needed in list view
                    insights_count=row.get("insights_count", 0),
                    created=str(row["created"]),
                    updated=str(row["updated"]),
                    # Status fields from fetched command
                    command_id=command_id,
                    status=status,
                    processing_info=processing_info,
                )
            )

        return response_list
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching sources: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching sources: {str(e)}")


@router.post("/sources", response_model=SourceResponse)
async def create_source(
    form_data: tuple[SourceCreate, Optional[UploadFile]] = Depends(
        parse_source_form_data
    ),
):
    """Create a new source with support for both JSON and multipart form data."""
    source_data, upload_file = form_data

    # Initialize file_path before try block so exception handlers can reference it
    file_path = None

    try:
        # Verify all specified notebooks exist (backward compatibility support)
        for notebook_id in source_data.notebooks or []:
            notebook = await Notebook.get(notebook_id)
            if not notebook:
                raise HTTPException(
                    status_code=404, detail=f"Notebook {notebook_id} not found"
                )

        # Handle file upload if provided
        if upload_file and source_data.type == "upload":
            try:
                file_path = await save_uploaded_file(upload_file)
            except Exception as e:
                logger.error(f"File upload failed: {e}")
                raise HTTPException(
                    status_code=400, detail=f"File upload failed: {str(e)}"
                )

        # Prepare content_state for processing
        content_state: dict[str, Any] = {}

        if source_data.type == "link":
            if not source_data.url:
                raise HTTPException(
                    status_code=400, detail="URL is required for link type"
                )
            content_state["url"] = source_data.url
        elif source_data.type == "upload":
            # Use uploaded file path or provided file_path (backward compatibility)
            final_file_path = file_path or source_data.file_path
            if not final_file_path:
                raise HTTPException(
                    status_code=400,
                    detail="File upload or file_path is required for upload type",
                )
            content_state["file_path"] = final_file_path
            content_state["delete_source"] = source_data.delete_source
        elif source_data.type == "text":
            if not source_data.content:
                raise HTTPException(
                    status_code=400, detail="Content is required for text type"
                )
            content_state["content"] = source_data.content
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid source type. Must be link, upload, or text",
            )

        # Validate transformations exist
        transformation_ids = source_data.transformations or []
        for trans_id in transformation_ids:
            transformation = await Transformation.get(trans_id)
            if not transformation:
                raise HTTPException(
                    status_code=404, detail=f"Transformation {trans_id} not found"
                )

        # Branch based on processing mode
        if source_data.async_processing:
            # ASYNC PATH: Create source record first, then queue command
            logger.info("Using async processing path")

            # Create minimal source record - let SurrealDB generate the ID
            source = Source(
                title=source_data.title or "Processing...",
                topics=[],
            )
            await source.save()

            # Add source to notebooks immediately so it appears in the UI
            # The source_graph will skip adding duplicates
            for notebook_id in source_data.notebooks or []:
                await source.add_to_notebook(notebook_id)

            try:
                # Import command modules to ensure they're registered
                import commands.source_commands  # noqa: F401

                # Submit command for background processing
                command_input = SourceProcessingInput(
                    source_id=str(source.id),
                    content_state=content_state,
                    notebook_ids=source_data.notebooks,
                    transformations=transformation_ids,
                    embed=source_data.embed,
                )

                command_id = await CommandService.submit_command_job(
                    "open_notebook",  # app name
                    "process_source",  # command name
                    command_input.model_dump(),
                )

                logger.info(f"Submitted async processing command: {command_id}")

                # Update source with command reference immediately
                # command_id already includes 'command:' prefix
                source.command = ensure_record_id(command_id)
                await source.save()

                # Return source with command info
                return SourceResponse(
                    id=source.id or "",
                    title=source.title,
                    topics=source.topics or [],
                    asset=None,  # Will be populated after processing
                    full_text=None,  # Will be populated after processing
                    embedded=False,  # Will be updated after processing
                    embedded_chunks=0,
                    created=str(source.created),
                    updated=str(source.updated),
                    command_id=command_id,
                    status="new",
                    processing_info={"async": True, "queued": True},
                )

            except Exception as e:
                logger.error(f"Failed to submit async processing command: {e}")
                # Clean up source record on command submission failure
                try:
                    await source.delete()
                except Exception:
                    pass
                # Clean up uploaded file if we created it
                if file_path and upload_file:
                    try:
                        os.unlink(file_path)
                    except Exception:
                        pass
                raise HTTPException(
                    status_code=500, detail=f"Failed to queue processing: {str(e)}"
                )

        else:
            # SYNC PATH: Execute synchronously using execute_command_sync
            logger.info("Using sync processing path")

            try:
                # Import command modules to ensure they're registered
                import commands.source_commands  # noqa: F401

                # Create source record - let SurrealDB generate the ID
                source = Source(
                    title=source_data.title or "Processing...",
                    topics=[],
                )
                await source.save()

                # Add source to notebooks immediately so it appears in the UI
                # The source_graph will skip adding duplicates
                for notebook_id in source_data.notebooks or []:
                    await source.add_to_notebook(notebook_id)

                # Execute command synchronously
                command_input = SourceProcessingInput(
                    source_id=str(source.id),
                    content_state=content_state,
                    notebook_ids=source_data.notebooks,
                    transformations=transformation_ids,
                    embed=source_data.embed,
                )

                # Run in thread pool to avoid blocking the event loop
                # execute_command_sync uses asyncio.run() internally which can't
                # be called from an already-running event loop (FastAPI)
                result = await asyncio.to_thread(
                    execute_command_sync,
                    "open_notebook",  # app name
                    "process_source",  # command name
                    command_input.model_dump(),
                    timeout=300,  # 5 minute timeout for sync processing
                )

                if not result.is_success():
                    logger.error(f"Sync processing failed: {result.error_message}")
                    # Clean up source record
                    try:
                        await source.delete()
                    except Exception:
                        pass
                    # Clean up uploaded file if we created it
                    if file_path and upload_file:
                        try:
                            os.unlink(file_path)
                        except Exception:
                            pass
                    raise HTTPException(
                        status_code=500,
                        detail=f"Processing failed: {result.error_message}",
                    )

                # Get the processed source
                if not source.id:
                    raise HTTPException(status_code=500, detail="Source ID is missing")
                processed_source = await Source.get(source.id)
                if not processed_source:
                    raise HTTPException(
                        status_code=500, detail="Processed source not found"
                    )

                embedded_chunks = await processed_source.get_embedded_chunks()
                return SourceResponse(
                    id=processed_source.id or "",
                    title=processed_source.title,
                    topics=processed_source.topics or [],
                    asset=AssetModel(
                        file_path=processed_source.asset.file_path
                        if processed_source.asset
                        else None,
                        url=processed_source.asset.url
                        if processed_source.asset
                        else None,
                    )
                    if processed_source.asset
                    else None,
                    full_text=processed_source.full_text,
                    embedded=embedded_chunks > 0,
                    embedded_chunks=embedded_chunks,
                    created=str(processed_source.created),
                    updated=str(processed_source.updated),
                    # No command_id or status for sync processing (legacy behavior)
                )

            except Exception as e:
                logger.error(f"Sync processing failed: {e}")
                # Clean up uploaded file if we created it
                if file_path and upload_file:
                    try:
                        os.unlink(file_path)
                    except Exception:
                        pass
                raise

    except HTTPException:
        # Clean up uploaded file on HTTP exceptions if we created it
        if file_path and upload_file:
            try:
                os.unlink(file_path)
            except Exception:
                pass
        raise
    except InvalidInputError as e:
        # Clean up uploaded file on validation errors if we created it
        if file_path and upload_file:
            try:
                os.unlink(file_path)
            except Exception:
                pass
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating source: {str(e)}")
        # Clean up uploaded file on unexpected errors if we created it
        if file_path and upload_file:
            try:
                os.unlink(file_path)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Error creating source: {str(e)}")


@router.post("/sources/json", response_model=SourceResponse)
async def create_source_json(source_data: SourceCreate):
    """Create a new source using JSON payload (legacy endpoint for backward compatibility)."""
    # Convert to form data format and call main endpoint
    form_data = (source_data, None)
    return await create_source(form_data)


@router.post(
    "/sources/common-graphs",
    response_model=CommonGraphResponse,
    status_code=201,
)
async def create_common_graph(request: CommonGraphCreate):
    """Create a persistent common graph from selected sources."""
    try:
        if not request.source_ids or len(request.source_ids) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least two source IDs are required to create a common graph.",
            )

        source_objects: List[Source] = []
        for source_id in request.source_ids:
            try:
                source = await Source.get(source_id)
            except NotFoundError:
                raise HTTPException(
                    status_code=404,
                    detail=f"Source {source_id} not found",
                )
            source_objects.append(source)

        graph_metadata = await _build_common_graph_metadata_llm(
            source_objects,
            model_id=request.model_id,
            prompt=request.prompt,
        ) if request.model_id else _build_common_graph_metadata(source_objects)
        metadata = {"created_from": "common_graph_ui", **graph_metadata}

        common_graph = CommonGraph(
            title=request.title,
            source_ids=request.source_ids,
            status="completed",
            metadata=metadata,
        )
        await common_graph.save()

        return CommonGraphResponse(
            id=common_graph.id or "",
            title=common_graph.title,
            source_ids=common_graph.source_ids,
            status=common_graph.status,
            metadata=common_graph.metadata,
            created=str(common_graph.created),
            updated=str(common_graph.updated),
        )
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating common graph: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating common graph: {str(e)}",
        )


@router.get("/sources/common-graphs/{common_graph_id}", response_model=CommonGraphResponse)
async def get_common_graph(common_graph_id: str):
    """Retrieve a previously saved common graph."""
    try:
        common_graph = await CommonGraph.get(common_graph_id)
        return CommonGraphResponse(
            id=common_graph.id or "",
            title=common_graph.title,
            source_ids=common_graph.source_ids,
            status=common_graph.status,
            metadata=common_graph.metadata,
            created=str(common_graph.created),
            updated=str(common_graph.updated),
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching common graph {common_graph_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching common graph: {str(e)}")


async def _resolve_source_file(source_id: str) -> tuple[str, str]:
    source = await Source.get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    file_path = source.asset.file_path if source.asset else None
    if not file_path:
        raise HTTPException(status_code=404, detail="Source has no file to download")

    safe_root = os.path.realpath(UPLOADS_FOLDER)
    resolved_path = os.path.realpath(file_path)

    if not resolved_path.startswith(safe_root):
        logger.warning(
            f"Blocked download outside uploads directory for source {source_id}: {resolved_path}"
        )
        raise HTTPException(status_code=403, detail="Access to file denied")

    if not os.path.exists(resolved_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    filename = os.path.basename(resolved_path)
    return resolved_path, filename


def _is_source_file_available(source: Source) -> Optional[bool]:
    if not source or not source.asset or not source.asset.file_path:
        return None

    file_path = source.asset.file_path
    safe_root = os.path.realpath(UPLOADS_FOLDER)
    resolved_path = os.path.realpath(file_path)

    if not resolved_path.startswith(safe_root):
        return False

    return os.path.exists(resolved_path)


@router.get("/sources/{source_id}", response_model=SourceResponse)
async def get_source(source_id: str, include_text: bool = True):
    """Get a specific source by ID. Pass include_text=false to skip full_text for faster loads."""
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Get status information if command exists
        status = None
        processing_info = None
        if source.command:
            try:
                status = await source.get_status()
                processing_info = await source.get_processing_progress()
            except Exception as e:
                logger.warning(f"Failed to get status for source {source_id}: {e}")
                status = "unknown"

        embedded_chunks = await source.get_embedded_chunks()

        # Get associated notebooks
        notebooks_query = await repo_query(
            "SELECT VALUE out FROM reference WHERE in = $source_id",
            {"source_id": ensure_record_id(source.id or source_id)},
        )
        notebook_ids = (
            [str(nb_id) for nb_id in notebooks_query] if notebooks_query else []
        )

        return SourceResponse(
            id=source.id or "",
            title=source.title,
            topics=source.topics or [],
            asset=AssetModel(
                file_path=source.asset.file_path if source.asset else None,
                url=source.asset.url if source.asset else None,
            )
            if source.asset
            else None,
            full_text=source.full_text if include_text else None,
            embedded=embedded_chunks > 0,
            embedded_chunks=embedded_chunks,
            file_available=_is_source_file_available(source),
            created=str(source.created),
            updated=str(source.updated),
            # Status fields
            command_id=str(source.command) if source.command else None,
            status=status,
            processing_info=processing_info,
            # Notebook associations
            notebooks=notebook_ids,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching source: {str(e)}")


@router.head("/sources/{source_id}/download")
async def check_source_file(source_id: str):
    """Check if a source has a downloadable file."""
    try:
        await _resolve_source_file(source_id)
        return Response(status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking file for source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to verify file")


@router.get("/sources/{source_id}/download")
async def download_source_file(source_id: str):
    """Download the original file associated with an uploaded source."""
    try:
        resolved_path, filename = await _resolve_source_file(source_id)
        return FileResponse(
            path=resolved_path,
            filename=filename,
            media_type="application/octet-stream",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file for source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download source file")


@router.get("/sources/{source_id}/status", response_model=SourceStatusResponse)
async def get_source_status(source_id: str):
    """Get processing status for a source."""
    try:
        # First, verify source exists
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Check if this is a legacy source (no command)
        if not source.command:
            return SourceStatusResponse(
                status=None,
                message="Legacy source (completed before async processing)",
                processing_info=None,
                command_id=None,
            )

        # Get command status and processing info
        try:
            status = await source.get_status()
            processing_info = await source.get_processing_progress()

            # Generate descriptive message based on status
            if status == "completed":
                message = "Source processing completed successfully"
            elif status == "failed":
                message = "Source processing failed"
            elif status == "running":
                message = "Source processing in progress"
            elif status == "queued":
                message = "Source processing queued"
            elif status == "unknown":
                message = "Source processing status unknown"
            else:
                message = f"Source processing status: {status}"

            return SourceStatusResponse(
                status=status,
                message=message,
                processing_info=processing_info,
                command_id=str(source.command) if source.command else None,
            )

        except Exception as e:
            logger.warning(f"Failed to get status for source {source_id}: {e}")
            return SourceStatusResponse(
                status="unknown",
                message="Failed to retrieve processing status",
                processing_info=None,
                command_id=str(source.command) if source.command else None,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching status for source {source_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching source status: {str(e)}"
        )


@router.put("/sources/{source_id}", response_model=SourceResponse)
async def update_source(source_id: str, source_update: SourceUpdate):
    """Update a source."""
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Update only provided fields
        if source_update.title is not None:
            source.title = source_update.title
        if source_update.topics is not None:
            source.topics = source_update.topics

        await source.save()

        embedded_chunks = await source.get_embedded_chunks()
        return SourceResponse(
            id=source.id or "",
            title=source.title,
            topics=source.topics or [],
            asset=AssetModel(
                file_path=source.asset.file_path if source.asset else None,
                url=source.asset.url if source.asset else None,
            )
            if source.asset
            else None,
            full_text=source.full_text,
            embedded=embedded_chunks > 0,
            embedded_chunks=embedded_chunks,
            created=str(source.created),
            updated=str(source.updated),
        )
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating source: {str(e)}")


@router.post("/sources/{source_id}/retry", response_model=SourceResponse)
async def retry_source_processing(source_id: str):
    """Retry processing for a failed or stuck source."""
    try:
        # First, verify source exists
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Check if source already has a running command
        if source.command:
            try:
                status = await source.get_status()
                if status in ["running", "queued"]:
                    raise HTTPException(
                        status_code=400,
                        detail="Source is already processing. Cannot retry while processing is active.",
                    )
            except Exception as e:
                logger.warning(
                    f"Failed to check current status for source {source_id}: {e}"
                )
                # Continue with retry if we can't check status

        # Get notebooks that this source belongs to
        query = "SELECT notebook FROM reference WHERE source = $source_id"
        references = await repo_query(query, {"source_id": source_id})
        notebook_ids = [str(ref["notebook"]) for ref in references]

        if not notebook_ids:
            raise HTTPException(
                status_code=400, detail="Source is not associated with any notebooks"
            )

        # Prepare content_state based on source asset
        content_state = {}
        if source.asset:
            if source.asset.file_path:
                content_state = {
                    "file_path": source.asset.file_path,
                    "delete_source": False,  # Don't delete on retry
                }
            elif source.asset.url:
                content_state = {"url": source.asset.url}
            else:
                raise HTTPException(
                    status_code=400, detail="Source asset has no file_path or url"
                )
        else:
            # Check if it's a text source by trying to get full_text
            if source.full_text:
                content_state = {"content": source.full_text}
            else:
                raise HTTPException(
                    status_code=400, detail="Cannot determine source content for retry"
                )

        try:
            # Import command modules to ensure they're registered
            import commands.source_commands  # noqa: F401

            # Submit new command for background processing
            command_input = SourceProcessingInput(
                source_id=str(source.id),
                content_state=content_state,
                notebook_ids=notebook_ids,
                transformations=[],  # Use default transformations on retry
                embed=True,  # Always embed on retry
            )

            command_id = await CommandService.submit_command_job(
                "open_notebook",  # app name
                "process_source",  # command name
                command_input.model_dump(),
            )

            logger.info(
                f"Submitted retry processing command: {command_id} for source {source_id}"
            )

            # Update source with new command ID
            source.command = ensure_record_id(f"command:{command_id}")
            await source.save()

            # Get current embedded chunks count
            embedded_chunks = await source.get_embedded_chunks()

            # Return updated source response
            return SourceResponse(
                id=source.id or "",
                title=source.title,
                topics=source.topics or [],
                asset=AssetModel(
                    file_path=source.asset.file_path if source.asset else None,
                    url=source.asset.url if source.asset else None,
                )
                if source.asset
                else None,
                full_text=source.full_text,
                embedded=embedded_chunks > 0,
                embedded_chunks=embedded_chunks,
                created=str(source.created),
                updated=str(source.updated),
                command_id=command_id,
                status="queued",
                processing_info={"retry": True, "queued": True},
            )

        except Exception as e:
            logger.error(
                f"Failed to submit retry processing command for source {source_id}: {e}"
            )
            raise HTTPException(
                status_code=500, detail=f"Failed to queue retry processing: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying source processing for {source_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error retrying source processing: {str(e)}"
        )


@router.delete("/sources/{source_id}")
async def delete_source(source_id: str):
    """Delete a source."""
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        await source.delete()

        return {"message": "Source deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting source: {str(e)}")


@router.get("/sources/{source_id}/insights", response_model=List[SourceInsightResponse])
async def get_source_insights(source_id: str):
    """Get all insights for a specific source."""
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        insights = await source.get_insights()
        return [
            SourceInsightResponse(
                id=insight.id or "",
                source_id=source_id,
                insight_type=insight.insight_type,
                content=insight.content,
                created=str(insight.created),
                updated=str(insight.updated),
            )
            for insight in insights
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching insights for source {source_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching insights: {str(e)}"
        )


@router.post(
    "/sources/{source_id}/insights",
    response_model=InsightCreationResponse,
    status_code=202,
)
async def create_source_insight(source_id: str, request: CreateSourceInsightRequest):
    """
    Start insight generation for a source by running a transformation.

    This endpoint returns immediately with a 202 Accepted status.
    The transformation runs asynchronously in the background via the job queue.
    Poll GET /sources/{source_id}/insights to see when the insight is ready.
    """
    try:
        # Validate source exists
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Validate transformation exists
        transformation = await Transformation.get(request.transformation_id)
        if not transformation:
            raise HTTPException(status_code=404, detail="Transformation not found")

        # Submit transformation as background job (fire-and-forget)
        command_id = submit_command(
            "open_notebook",
            "run_transformation",
            {
                "source_id": source_id,
                "transformation_id": request.transformation_id,
            },
        )
        logger.info(
            f"Submitted run_transformation command {command_id} for source {source_id}"
        )

        # Return immediately with command_id for status tracking
        return InsightCreationResponse(
            status="pending",
            message="Insight generation started",
            source_id=source_id,
            transformation_id=request.transformation_id,
            command_id=str(command_id),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting insight generation for source {source_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error starting insight generation: {str(e)}"
        )

