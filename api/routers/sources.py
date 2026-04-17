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

    # Try transformer model first (most accurate for person NER)
    for model_name in ("en_core_web_trf", "en_core_web_lg", "en_core_web_md", "en_core_web_sm"):
        try:
            _spacy_nlp = spacy.load(model_name)
            logger.info(f"[spaCy] Loaded model: {model_name}")
            return _spacy_nlp
        except OSError:
            continue

    logger.warning(
        "No spaCy model found. "
        "Install with: python -m spacy download en_core_web_trf"
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


# ── Comprehensive entity extraction: persons, activities, relationships ──────
# Uses BERT (all-MiniLM-L6-v2) for semantic matching + IR patterns for extraction

_sbert_model = None


def _get_sbert_model():
    global _sbert_model
    if _sbert_model is not None:
        return _sbert_model
    try:
        from sentence_transformers import SentenceTransformer
        _sbert_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("[CommonGraph] Loaded all-MiniLM-L6-v2")
        return _sbert_model
    except Exception as e:
        logger.warning(f"[CommonGraph] BERT load failed: {e}")
        return None


_WORD_BLOCKLIST = {
    'name', 'names', 'full', 'alias', 'parentage', 'address', 'occupation',
    'age', 'status', 'education', 'contact', 'mobile', 'email', 'mail',
    'residence', 'resident', 'permanent', 'present', 'current', 'date',
    'sir', 'mr', 'mrs', 'ms', 'dr', 'shri', 'smt', 'km', 'late',
    'son', 'daughter', 'wife', 'husband', 'brother', 'sister',
    'father', 'mother', 'uncle', 'aunt', 'nephew', 'niece',
    'accused', 'victim', 'complainant', 'witness', 'suspect', 'informer',
    'officer', 'inspector', 'constable', 'head', 'sub', 'senior', 'junior',
    'police', 'judge', 'advocate', 'counsel', 'magistrate', 'station',
    'india', 'delhi', 'haryana', 'rajasthan', 'punjab', 'gujarat', 'mumbai',
    'uttar', 'pradesh', 'madhya', 'bihar', 'bengal', 'chennai', 'kolkata',
    'district', 'village', 'city', 'town', 'road', 'street', 'nagar',
    'colony', 'sector', 'phase', 'block', 'flat', 'house', 'near',
    'the', 'and', 'or', 'of', 'in', 'at', 'to', 'for', 'with', 'from',
    'said', 'told', 'asked', 'stated', 'mentioned', 'informed', 'reported',
    'case', 'fir', 'section', 'act', 'ipc', 'crpc', 'court',
    'unknown', 'male', 'female', 'married', 'unmarried', 'single',
    'january', 'february', 'march', 'april', 'may', 'june',
    'july', 'august', 'september', 'october', 'november', 'december',
}


def _clean_person_name(raw):
    """Clean, validate and properly space a person name."""
    import re as _re
    # Normalize whitespace
    s = _re.sub(r'\s+', ' ', raw.strip())
    # Remove trailing punctuation
    s = s.rstrip('.,;:()[]')
    # Must be 3-60 chars
    if len(s) < 3 or len(s) > 60:
        return ''
    # Must start with uppercase
    if not s[0].isupper():
        return ''
    # Must have at least one alpha char
    if not any(c.isalpha() for c in s):
        return ''
    # Check blocklist
    norm = s.lower()
    words = [w for w in norm.split() if w.isalpha()]
    if not words:
        return ''
    if all(w in _WORD_BLOCKLIST for w in words):
        return ''
    if words[0] in _WORD_BLOCKLIST:
        return ''
    return s


def _take_name_words(raw, max_words=4):
    """
    Take up to max_words words from raw that form a valid person name.
    Stops at lowercase words, blocklist words, or numbers.
    Handles '@' alias notation (e.g. 'Sandeep @ Kala Jathedi').
    """
    import re as _re
    # Split on whitespace
    words = raw.strip().split()
    clean = []
    i = 0
    while i < len(words) and len(clean) < max_words:
        w = words[i]
        # Handle @ alias separator
        if w == '@' and clean:
            clean.append(w)
            i += 1
            continue
        # Strip non-alpha from word for checking
        alpha = _re.sub(r'[^a-zA-Z]', '', w)
        if not alpha:
            break
        # Stop at blocklist
        if alpha.lower() in _WORD_BLOCKLIST:
            break
        # Stop at lowercase start (unless it's after @)
        if not alpha[0].isupper() and (not clean or clean[-1] != '@'):
            break
        clean.append(w)
        i += 1
    # Remove trailing @
    while clean and clean[-1] == '@':
        clean.pop()
    return ' '.join(clean).strip()


def _extract_all_entities(text):
    """
    Extract from IR document text:
    - persons (named individuals with roles)
    - activities (crimes, weapons, drugs, events, transactions)
    - relationships (family, associates, gang members)

    Returns:
        persons: dict {norm -> {label, role}}
        activities: list of {label, type}
        relations: list of {from, to, type, label}
    """
    import re as _re

    persons = {}
    activities = []
    relations = []
    seen_rel = set()
    seen_act = set()
    current_main = None

    lines = text.split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # ── Structured field patterns (Name:, Accused:, etc.) ────────────
        for pat, role in [
            (r'^(?:Name|Full\s*Name)\s*[:\-]\s*(.+)', 'main'),
            (r'^Accused\s*[:\-]\s*(.+)', 'accused'),
            (r'^(?:Victim|Complainant)\s*[:\-]\s*(.+)', 'victim'),
            (r'^(?:Witness|Informer)\s*[:\-]\s*(.+)', 'witness'),
            (r'^Suspect\s*[:\-]\s*(.+)', 'suspect'),
        ]:
            m = _re.match(pat, line, _re.IGNORECASE)
            if m:
                raw = m.group(1).strip()
                name = _clean_person_name(_take_name_words(raw))
                if name:
                    norm = name.lower()
                    if norm not in persons:
                        persons[norm] = {'label': name, 'role': role}
                    if role in ('main', 'accused', 'victim', 'witness'):
                        current_main = name

        # ── Honorific prefix (Sh., Smt., Mr., etc.) ──────────────────────
        for m in _re.finditer(
            r'\b(?:Sh\.|Shri|Smt\.|Km\.|Mr\.|Mrs\.|Dr\.)\s+([A-Z][a-zA-Z\s@]{2,40})',
            line
        ):
            name = _clean_person_name(_take_name_words(m.group(1)))
            if name:
                norm = name.lower()
                if norm not in persons:
                    persons[norm] = {'label': name, 'role': 'person'}

        # ── Verb + name (arrested, nabbed, etc.) ─────────────────────────
        for m in _re.finditer(
            r'\b(?:arrested|nabbed|apprehended|detained|identified)\s+([A-Z][a-zA-Z\s@]{2,40})',
            line, _re.IGNORECASE
        ):
            name = _clean_person_name(_take_name_words(m.group(1)))
            if name:
                norm = name.lower()
                if norm not in persons:
                    persons[norm] = {'label': name, 'role': 'accused'}

        # ── Family relationship patterns ──────────────────────────────────
        for pat, rel_label in [
            (r'\bS/O\s+([A-Z][a-zA-Z\s@]{2,40})', 'father'),
            (r'\bD/O\s+([A-Z][a-zA-Z\s@]{2,40})', 'father'),
            (r'\bW/O\s+([A-Z][a-zA-Z\s@]{2,40})', 'husband'),
            (r'\bSon\s+of\s+([A-Z][a-zA-Z\s@]{2,40})', 'father'),
            (r'\bDaughter\s+of\s+([A-Z][a-zA-Z\s@]{2,40})', 'father'),
            (r'\bWife\s+of\s+([A-Z][a-zA-Z\s@]{2,40})', 'husband'),
            (r'\bBrother\s+of\s+([A-Z][a-zA-Z\s@]{2,40})', 'brother'),
            (r'\bSister\s+of\s+([A-Z][a-zA-Z\s@]{2,40})', 'sister'),
            (r'\bMother\s+of\s+([A-Z][a-zA-Z\s@]{2,40})', 'mother'),
            (r'\bFather\s+of\s+([A-Z][a-zA-Z\s@]{2,40})', 'father'),
        ]:
            for m in _re.finditer(pat, line, _re.IGNORECASE):
                rel_name = _clean_person_name(_take_name_words(m.group(1)))
                if rel_name and current_main:
                    norm_r = rel_name.lower()
                    if norm_r not in persons:
                        persons[norm_r] = {'label': rel_name, 'role': 'relative'}
                    key = (current_main.lower(), norm_r, rel_label)
                    if key not in seen_rel:
                        seen_rel.add(key)
                        relations.append({
                            'from': current_main,
                            'to': rel_name,
                            'type': 'family',
                            'label': rel_label,
                        })

        # ── Associate/gang patterns ───────────────────────────────────────
        for pat, rel_label in [
            (r'\b(?:associate|associates)\s+(?:of\s+)?([A-Z][a-zA-Z\s@]{2,40})', 'associate'),
            (r'\b(?:gang\s+member|gang\s+associate)\s+([A-Z][a-zA-Z\s@]{2,40})', 'gang member'),
            (r'\b(?:friend|close\s+friend)\s+(?:of\s+)?([A-Z][a-zA-Z\s@]{2,40})', 'friend'),
            (r'\b(?:co-accused|co\s+accused)\s+([A-Z][a-zA-Z\s@]{2,40})', 'co-accused'),
            (r'\b(?:partner|accomplice)\s+(?:of\s+)?([A-Z][a-zA-Z\s@]{2,40})', 'accomplice'),
        ]:
            for m in _re.finditer(pat, line, _re.IGNORECASE):
                assoc_name = _clean_person_name(_take_name_words(m.group(1)))
                if assoc_name and current_main:
                    norm_a = assoc_name.lower()
                    if norm_a not in persons:
                        persons[norm_a] = {'label': assoc_name, 'role': 'associate'}
                    key = (current_main.lower(), norm_a, rel_label)
                    if key not in seen_rel:
                        seen_rel.add(key)
                        relations.append({
                            'from': current_main,
                            'to': assoc_name,
                            'type': 'associate',
                            'label': rel_label,
                        })

        # ── Activity patterns ─────────────────────────────────────────────
        line_lower = line.lower()
        for keywords, act_type in [
            (['robbery', 'theft', 'murder', 'assault', 'kidnapping', 'extortion',
              'fraud', 'smuggling', 'trafficking', 'dacoity', 'rape', 'abduction',
              'cheating', 'forgery', 'bribery', 'loot', 'snatching'], 'crime'),
            (['pistol', 'revolver', 'rifle', 'gun', 'knife', 'sword', 'bomb',
              'explosive', 'weapon', 'arms', 'ammunition', 'cartridge'], 'weapon'),
            (['drugs', 'drug', 'narcotics', 'heroin', 'cocaine', 'ganja',
              'smack', 'charas', 'afeem', 'opium', 'mdma'], 'drug'),
            (['money laundering', 'hawala', 'ransom', 'extortion money',
              'cash recovery', 'illegal payment'], 'transaction'),
            (['meeting', 'encounter', 'arrest', 'raid', 'recovery', 'seizure',
              'incident', 'attack', 'firing', 'chase', 'escape'], 'event'),
        ]:
            for kw in keywords:
                if kw in line_lower and kw not in seen_act:
                    seen_act.add(kw)
                    activities.append({'label': kw, 'type': act_type})

    return persons, activities, relations


def _get_sentences(text):
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if len(line) > 20 and not line.endswith(':'):
            lines.append(line)
    return lines


def _normalize(s):
    return s.lower().strip()


def _extract_personal_details(text):
    """Extract personal details fields from IR document."""
    import re as _re
    details = {}
    field_patterns = [
        (r'^(?:Name|Full\s*Name)\s*[:\-]\s*(.+)', 'Name'),
        (r'^(?:Age|DOB|Date\s*of\s*Birth)\s*[:\-]\s*(.+)', 'Age/DOB'),
        (r'^(?:Address|Residence|Permanent\s*Address|Present\s*Address)\s*[:\-]\s*(.+)', 'Address'),
        (r'^(?:Occupation|Profession)\s*[:\-]\s*(.+)', 'Occupation'),
        (r'^(?:Education|Qualification)\s*[:\-]\s*(.+)', 'Education'),
        (r'^(?:Mobile|Contact|Phone)\s*[:\-]\s*(.+)', 'Contact'),
        (r'^(?:Email|E-mail)\s*[:\-]\s*(.+)', 'Email'),
        (r'^(?:Nationality|Religion|Caste)\s*[:\-]\s*(.+)', 'Nationality'),
        (r'^(?:Marital\s*Status|Status)\s*[:\-]\s*(.+)', 'Marital Status'),
        (r'^(?:FIR|Case\s*No|Case\s*Number)\s*[:\-]\s*(.+)', 'Case No'),
        (r'^(?:Section|Sections|Offence)\s*[:\-]\s*(.+)', 'Offence'),
        (r'^(?:Police\s*Station|PS)\s*[:\-]\s*(.+)', 'Police Station'),
        (r'^(?:District)\s*[:\-]\s*(.+)', 'District'),
        (r'^(?:State)\s*[:\-]\s*(.+)', 'State'),
        (r'^(?:Accused|Victim|Complainant|Witness)\s*[:\-]\s*(.+)', 'Role'),
    ]
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        for pat, field_name in field_patterns:
            m = _re.match(pat, line, _re.IGNORECASE)
            if m and field_name not in details:
                val = m.group(1).strip().rstrip('.,;')
                if val and len(val) < 200:
                    details[field_name] = val
    return details


def _build_personal_graph(source_idx, source_title, details):
    """Build a star graph: center=person, spokes=personal detail fields."""
    nodes = []
    links = []

    # Center node = the person
    person_name = details.get('Name', source_title.replace('.docx', '').replace('.doc', '').strip())
    center_id = f'center:{source_idx}'
    nodes.append({
        'id': center_id,
        'label': person_name,
        'type': 'person',
        'role': details.get('Role', 'main'),
        'common': True,
        'weight': 3,
    })

    # Detail nodes
    skip_fields = {'Name', 'Role'}
    for i, (field, value) in enumerate(details.items()):
        if field in skip_fields:
            continue
        nid = f'detail:{source_idx}:{i}'
        # Truncate long values
        display_val = value if len(value) <= 30 else value[:28] + '…'
        nodes.append({
            'id': nid,
            'label': display_val,
            'type': 'detail',
            'field': field,
            'weight': 1,
            'common': False,
        })
        links.append({
            'source': center_id,
            'target': nid,
            'type': 'detail',
            'label': field,
            'weight': 1,
        })

    return {'nodes': nodes, 'links': links}


def _build_family_graph(source_idx, source_title, persons, relations):
    """Build family tree graph for a source document."""
    nodes = []
    links = []
    node_ids = {}

    # Find main person
    main_person = None
    for norm, info in persons.items():
        if info['role'] in ('main', 'accused', 'victim'):
            main_person = info['label']
            break
    if not main_person and persons:
        main_person = list(persons.values())[0]['label']
    if not main_person:
        main_person = source_title.replace('.docx', '').strip()

    # Center = main person
    center_id = f'fam_center:{source_idx}'
    node_ids[main_person.lower()] = center_id
    nodes.append({
        'id': center_id,
        'label': main_person,
        'type': 'person',
        'role': 'main',
        'common': True,
        'weight': 3,
    })

    # Family relations only
    family_labels = {'father', 'mother', 'husband', 'wife', 'brother', 'sister', 'son', 'daughter', 'uncle', 'aunt'}
    for rel in relations:
        if rel['type'] != 'family':
            continue
        rel_name = rel['to']
        rel_label = rel['label']
        norm_r = rel_name.lower()
        if norm_r not in node_ids:
            nid = f'fam_rel:{source_idx}:{len(node_ids)}'
            node_ids[norm_r] = nid
            nodes.append({
                'id': nid,
                'label': rel_name,
                'type': 'relative',
                'role': rel_label,
                'common': False,
                'weight': 1,
            })
        from_id = node_ids.get(rel['from'].lower(), center_id)
        to_id = node_ids[norm_r]
        links.append({
            'source': from_id,
            'target': to_id,
            'type': 'family',
            'label': rel_label,
            'weight': 2,
        })

    # Also add relatives found in persons dict
    for norm, info in persons.items():
        if info['role'] == 'relative' and norm not in node_ids:
            nid = f'fam_rel:{source_idx}:{len(node_ids)}'
            node_ids[norm] = nid
            nodes.append({
                'id': nid,
                'label': info['label'],
                'type': 'relative',
                'role': 'relative',
                'common': False,
                'weight': 1,
            })
            links.append({
                'source': center_id,
                'target': nid,
                'type': 'family',
                'label': 'relative',
                'weight': 1,
            })

    return {'nodes': nodes, 'links': links}


def _build_associates_graph(source_idx, source_title, persons, relations, activities):
    """Build associates/gang/friends graph for a source document."""
    nodes = []
    links = []
    node_ids = {}

    # Find main person
    main_person = None
    for norm, info in persons.items():
        if info['role'] in ('main', 'accused', 'victim'):
            main_person = info['label']
            break
    if not main_person and persons:
        main_person = list(persons.values())[0]['label']
    if not main_person:
        main_person = source_title.replace('.docx', '').strip()

    center_id = f'assoc_center:{source_idx}'
    node_ids[main_person.lower()] = center_id
    nodes.append({
        'id': center_id,
        'label': main_person,
        'type': 'person',
        'role': 'main',
        'common': True,
        'weight': 3,
    })

    # Associates, gang, friends, co-accused
    assoc_types = {'associate', 'gang member', 'friend', 'co-accused', 'accomplice'}
    for rel in relations:
        if rel['type'] not in ('associate',) and rel['label'] not in assoc_types:
            continue
        assoc_name = rel['to']
        norm_a = assoc_name.lower()
        if norm_a not in node_ids:
            nid = f'assoc:{source_idx}:{len(node_ids)}'
            node_ids[norm_a] = nid
            nodes.append({
                'id': nid,
                'label': assoc_name,
                'type': 'person',
                'role': rel['label'],
                'common': False,
                'weight': 1,
            })
        from_id = node_ids.get(rel['from'].lower(), center_id)
        to_id = node_ids[norm_a]
        links.append({
            'source': from_id,
            'target': to_id,
            'type': 'associate',
            'label': rel['label'],
            'weight': 2,
        })

    # Add all accused persons as associates if no explicit relations found
    if len(nodes) <= 1:
        for norm, info in persons.items():
            if info['role'] in ('accused', 'suspect') and norm != main_person.lower():
                if norm not in node_ids:
                    nid = f'assoc:{source_idx}:{len(node_ids)}'
                    node_ids[norm] = nid
                    nodes.append({
                        'id': nid,
                        'label': info['label'],
                        'type': 'person',
                        'role': info['role'],
                        'common': False,
                        'weight': 1,
                    })
                    links.append({
                        'source': center_id,
                        'target': nid,
                        'type': 'associate',
                        'label': info['role'],
                        'weight': 1,
                    })

    # Activity nodes connected to center
    for i, act in enumerate(activities[:10]):
        nid = f'assoc_act:{source_idx}:{i}'
        nodes.append({
            'id': nid,
            'label': act['label'],
            'type': 'activity',
            'activity_type': act['type'],
            'common': False,
            'weight': 1,
        })
        links.append({
            'source': center_id,
            'target': nid,
            'type': 'activity',
            'label': act['type'],
            'weight': 1,
        })

    return {'nodes': nodes, 'links': links}


async def _build_common_graph_metadata_llm(sources, model_id, prompt=None):
    """
    Comprehensive graph: persons + activities + relationships.
    BERT semantic matching finds cross-doc connections.
    """
    import re as _re

    all_persons = []
    all_activities = []
    all_relations = []
    all_sentences = []

    for source in sources:
        text = source.full_text or source.title or ''
        persons, activities, relations = _extract_all_entities(text)
        all_persons.append(persons)
        all_activities.append(activities)
        all_relations.append(relations)
        all_sentences.append(_get_sentences(text))
        logger.info(
            f"[CommonGraph] '{source.title}': "
            f"{len(persons)} persons, {len(activities)} activities, {len(relations)} relations"
        )

    # ── BERT semantic matching ────────────────────────────────────────────
    sbert = _get_sbert_model()
    if sbert is not None and len(sources) >= 2:
        try:
            from sentence_transformers import util as su
            for i in range(len(sources)):
                for j in range(i + 1, len(sources)):
                    si = all_sentences[i][:200]
                    sj = all_sentences[j][:200]
                    if not si or not sj:
                        continue
                    ei = sbert.encode(si, convert_to_tensor=True, show_progress_bar=False)
                    ej = sbert.encode(sj, convert_to_tensor=True, show_progress_bar=False)
                    scores = su.cos_sim(ei, ej)
                    for a in range(len(si)):
                        for b in range(len(sj)):
                            if float(scores[a][b]) > 0.72:
                                for sent, doc_idx in [(si[a], i), (sj[b], j)]:
                                    p, act, rel = _extract_all_entities(sent)
                                    for norm, info in p.items():
                                        if norm not in all_persons[doc_idx]:
                                            all_persons[doc_idx][norm] = info
                                    for a_item in act:
                                        if a_item not in all_activities[doc_idx]:
                                            all_activities[doc_idx].append(a_item)
        except Exception as e:
            logger.warning(f"[CommonGraph] BERT matching failed: {e}")

    # ── Build unified maps ────────────────────────────────────────────────
    person_map = {}
    for doc_idx, persons in enumerate(all_persons):
        for norm, info in persons.items():
            if norm not in person_map:
                person_map[norm] = {'label': info['label'], 'role': info['role'], 'doc_indices': set()}
            person_map[norm]['doc_indices'].add(doc_idx)

    activity_map = {}
    for doc_idx, activities in enumerate(all_activities):
        for act in activities:
            key = act['label']
            if key not in activity_map:
                activity_map[key] = {'label': act['label'], 'type': act['type'], 'doc_indices': set()}
            activity_map[key]['doc_indices'].add(doc_idx)

    if not person_map and not activity_map:
        logger.warning("[CommonGraph] Nothing extracted, falling back to term extraction")
        return _build_common_graph_metadata(sources)

    # ── Build graph ───────────────────────────────────────────────────────
    nodes = []
    links = []
    node_ids = {}

    # Source nodes
    for idx, source in enumerate(sources):
        nid = f'source:{idx}'
        nodes.append({
            'id': nid,
            'label': source.title or f'Source {idx + 1}',
            'type': 'source',
            'source_id': source.id,
        })

    # Person nodes — sorted: common first, then by label
    sorted_persons = sorted(
        person_map.values(),
        key=lambda x: (-len(x['doc_indices']), x['label'])
    )
    for i, ent in enumerate(sorted_persons):
        norm = ent['label'].lower()
        nid = f'person:{i}'
        node_ids[norm] = nid
        is_common = len(ent['doc_indices']) >= 2
        nodes.append({
            'id': nid,
            'label': ent['label'],
            'type': 'person',
            'role': ent['role'],
            'weight': len(ent['doc_indices']),
            'common': is_common,
        })
        for src_idx in sorted(ent['doc_indices']):
            links.append({
                'source': f'source:{src_idx}',
                'target': nid,
                'type': 'appears_in',
                'weight': 1,
            })

    # Activity nodes
    sorted_acts = sorted(
        activity_map.values(),
        key=lambda x: (-len(x['doc_indices']), x['label'])
    )
    for i, act in enumerate(sorted_acts):
        nid = f'activity:{i}'
        node_ids[act['label']] = nid
        is_common = len(act['doc_indices']) >= 2
        nodes.append({
            'id': nid,
            'label': act['label'],
            'type': 'activity',
            'activity_type': act['type'],
            'weight': len(act['doc_indices']),
            'common': is_common,
        })
        for src_idx in sorted(act['doc_indices']):
            links.append({
                'source': f'source:{src_idx}',
                'target': nid,
                'type': 'appears_in',
                'weight': 1,
            })

    # Relationship links
    seen_links = set()
    for doc_relations in all_relations:
        for rel in doc_relations:
            from_norm = rel['from'].lower()
            to_norm = rel['to'].lower()
            from_id = node_ids.get(from_norm)
            to_id = node_ids.get(to_norm)

            if to_id is None:
                rid = f'relative:{len(node_ids)}'
                node_ids[to_norm] = rid
                to_id = rid
                nodes.append({
                    'id': rid,
                    'label': rel['to'],
                    'type': 'relative',
                    'role': rel['type'],
                    'weight': 1,
                    'common': False,
                })

            if from_id and to_id:
                link_key = f'{from_id}|{to_id}|{rel["label"]}'
                if link_key not in seen_links:
                    seen_links.add(link_key)
                    links.append({
                        'source': from_id,
                        'target': to_id,
                        'type': rel['type'],
                        'label': rel['label'],
                        'weight': 2,
                    })

    common_terms = [e['label'] for e in sorted_persons if e.get('common')]
    common_terms += [a['label'] for a in sorted_acts if a.get('common')]

    # ── Build 3 separate graphs per source ───────────────────────────────
    personal_graphs = []
    family_graphs = []
    associates_graphs = []

    for src_idx, source in enumerate(sources):
        text = source.full_text or source.title or ''
        details = _extract_personal_details(text)
        pg = _build_personal_graph(src_idx, source.title or f'Source {src_idx+1}', details)
        fg = _build_family_graph(src_idx, source.title or f'Source {src_idx+1}', all_persons[src_idx], all_relations[src_idx])
        ag = _build_associates_graph(src_idx, source.title or f'Source {src_idx+1}', all_persons[src_idx], all_relations[src_idx], all_activities[src_idx])
        personal_graphs.append({'source_title': source.title or f'Source {src_idx+1}', 'graph': pg})
        family_graphs.append({'source_title': source.title or f'Source {src_idx+1}', 'graph': fg})
        associates_graphs.append({'source_title': source.title or f'Source {src_idx+1}', 'graph': ag})

    logger.info(
        f"[CommonGraph] Final: {len(nodes)} nodes, {len(links)} links, "
        f"{sum(1 for n in nodes if n.get('common'))} common"
    )

    return {
        'common_terms': common_terms,
        'graph': {'nodes': nodes, 'links': links},
        'graph_type': 'network',
        'person_count': len(sorted_persons),
        'activity_count': len(sorted_acts),
        'common_count': sum(1 for n in nodes if n.get('common')),
        'personal_graphs': personal_graphs,
        'family_graphs': family_graphs,
        'associates_graphs': associates_graphs,
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


@router.get("/sources/{source_id}/profile-graph")
async def get_source_profile_graph(source_id: str, model_id: Optional[str] = Query(None)):
    """Dynamically extract personal details, family, and associates using LLM."""
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        text = source.full_text or source.title or ''

        # Try LLM extraction first if model available
        if model_id:
            try:
                result = await _extract_profile_graph_llm(text, model_id)
                result['source_id'] = source_id
                result['source_title'] = source.title or 'Unknown'
                return result
            except Exception as e:
                logger.warning(f"LLM profile extraction failed: {e}, falling back to regex")

        # Fallback to regex
        result = _extract_profile_graph(text)
        result['source_id'] = source_id
        result['source_title'] = source.title or 'Unknown'
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting profile graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _extract_profile_graph_llm(text: str, model_id: str) -> dict:
    """
    Use LLM to dynamically extract ALL fields present in the document.
    Returns structured data without hardcoded field names.
    """
    from langchain_core.messages import HumanMessage, SystemMessage
    from open_notebook.ai.provision import provision_langchain_model
    import json as _json
    import re as _re

    system_prompt = """You are an expert at extracting structured information from Indian Police Investigation Reports (IR) and case documents.

Analyze the document carefully and extract EVERY piece of personal information about the PRIMARY SUBJECT (main accused/victim).

Return a JSON object with exactly this structure:
{
  "main_person": "full name of the primary subject",
  "personal": {
    "Name": "full name",
    "Alias": "alias or nick name if any",
    "Age": "age",
    "Date of Birth": "DOB",
    "Gender": "Male/Female",
    "Parentage": "father's name (S/O or D/O)",
    "Address": "full address",
    "Occupation": "job/work",
    "Education": "qualification",
    "Mobile": "phone number",
    "Marital Status": "married/unmarried",
    "Complexion": "fair/dark/wheatish",
    "Height": "height",
    "Eyes": "eye color",
    "Hair": "hair color/type",
    "Build": "body build",
    "Mark of Identification": "any marks/moles/tattoos",
    "Facebook ID": "facebook profile if mentioned",
    "Criminal Record": "previous cases if any",
    "Case No": "FIR/case number",
    "Sections": "IPC sections",
    "Police Station": "PS name",
    "District": "district",
    "State": "state",
    "Role": "accused/victim/witness"
  },
  "family": [...],
  "associates": [...]
}

IMPORTANT:
- Only include fields that are ACTUALLY PRESENT in the document
- Extract the EXACT values as written in the document
- Do NOT include fields that are not in the document — omit them entirely
- Do NOT use null, None, or empty string values — skip missing fields
- For personal dict: use the field names exactly as shown above
- Return ONLY the JSON object, no explanation, no markdown"""

    truncated = text[:6000]
    payload = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=truncated),
    ]

    chain = await provision_langchain_model(str(payload), model_id, "transformation", max_tokens=2048)
    response = await chain.ainvoke(payload)
    raw = str(response.content if hasattr(response, 'content') else response).strip()
    logger.info(f"[ProfileGraph] LLM raw response: {raw}")

    # Strip markdown fences
    if '```' in raw:
        raw = _re.sub(r'```(?:json)?\s*', '', raw).strip()

    # Extract JSON object
    start = raw.find('{')
    end = raw.rfind('}')
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object in LLM response: {raw[:200]}")

    json_str = raw[start:end + 1]

    # Fix common LLM JSON issues:
    # 1. Replace Python None with null
    json_str = json_str.replace(': None', ': null').replace(':None', ':null')
    # 2. Replace trailing commas before } or ]
    json_str = _re.sub(r',\s*([}\]])', r'\1', json_str)
    # 3. Replace single quotes with double quotes (carefully)
    # Only do this if standard parse fails
    try:
        data = _json.loads(json_str)
    except _json.JSONDecodeError as e:
        logger.warning(f"[ProfileGraph] JSON parse error: {e}, trying cleanup")
        # Remove null values that might be causing issues
        json_str = _re.sub(r'"[^"]+"\s*:\s*null\s*,?\s*', '', json_str)
        json_str = _re.sub(r',\s*([}\]])', r'\1', json_str)
        data = _json.loads(json_str)

    # Normalize
    personal = data.get('personal', {})
    if not isinstance(personal, dict):
        personal = {}
    # Ensure all values are strings (LLM may return numbers, lists, etc.)
    personal = {
        str(k): str(v) if not isinstance(v, (list, dict)) else ', '.join(str(i) for i in v) if isinstance(v, list) else str(v)
        for k, v in personal.items()
        if v is not None and str(v).strip()
    }

    family = []
    for p in data.get('family', []):
        if isinstance(p, dict) and p.get('name'):
            family.append({
                'name': str(p.get('name', '')).strip(),
                'relation': str(p.get('relation', 'relative')).strip(),
                'gender': str(p.get('gender', 'male')).strip(),
                'details': str(p.get('details', '')).strip(),
            })

    associates = []
    for p in data.get('associates', []):
        if isinstance(p, dict) and p.get('name'):
            associates.append({
                'name': str(p.get('name', '')).strip(),
                'relation': str(p.get('relation', 'associate')).strip(),
                'gender': str(p.get('gender', 'male')).strip(),
                'details': str(p.get('details', '')).strip(),
            })

    logger.info(f"[ProfileGraph] LLM extracted: {len(personal)} fields, {len(family)} family, {len(associates)} associates")

    return {
        'main_person': str(data.get('main_person', '')).strip(),
        'personal': personal,
        'family': family,
        'associates': associates,
    }


def _extract_profile_graph(text: str) -> dict:
    """
    Comprehensive regex extraction from IR documents.
    Extracts ALL fields present — not just predefined ones.
    """
    import re as _re

    personal = {}
    family = []
    associates = []
    seen = set()

    def _guess_gender(name: str, relation: str) -> str:
        female_rel = {'mother', 'wife', 'sister', 'daughter', 'aunt', 'niece', 'girlfriend', 'smt', 'km', 'beti', 'behen', 'mata'}
        male_rel = {'father', 'husband', 'brother', 'son', 'uncle', 'nephew', 'boyfriend', 'sh', 'shri', 'beta', 'bhai', 'pita'}
        rl = relation.lower()
        if any(r in rl for r in female_rel): return 'female'
        if any(r in rl for r in male_rel): return 'male'
        female_sfx = ('a', 'i', 'devi', 'bai', 'kumari', 'rani', 'priya', 'lata', 'vati', 'wati')
        if any(name.lower().endswith(s) for s in female_sfx): return 'female'
        return 'male'

    def _clean(s: str) -> str:
        s = _re.sub(r'\s+', ' ', s.strip())
        return s.rstrip('.,;:()[]').strip()

    def _take_name(raw: str) -> str:
        words = raw.strip().split()[:5]
        clean = []
        bl = {'unknown', 'nil', 'n/a', 'na', 'not', 'available', 'mentioned', 'none', '-'}
        for w in words:
            alpha = _re.sub(r'[^a-zA-Z@]', '', w)
            if not alpha or alpha.lower() in bl: break
            if not (alpha[0].isupper() or alpha == '@'): break
            clean.append(w)
        while clean and clean[-1] == '@': clean.pop()
        return ' '.join(clean).strip()

    # ── Step 1: Extract ALL "Field: Value" pairs dynamically ──────────────
    # This catches ANY field in the document, not just predefined ones
    field_value_pattern = _re.compile(
        r'^([A-Za-z][A-Za-z\s/\(\)]{1,40}?)\s*[:\-]\s*(.+)$',
        _re.MULTILINE
    )

    # Fields to skip (they are not personal details)
    skip_fields = {
        'note', 'remarks', 'description', 'summary', 'details', 'information',
        'subject', 'report', 'date', 'time', 'place', 'location', 'source',
        'reference', 'sr no', 'serial', 'sl no', 'page', 'section',
    }

    # Multi-line field accumulator (for address etc.)
    lines = text.split('\n')
    current_field = None
    current_value_parts = []
    current_person_name = None

    def _flush_field():
        nonlocal current_field, current_value_parts
        if current_field and current_value_parts:
            val = _clean(' '.join(current_value_parts))
            if val and val.lower() not in ('nil', 'n/a', 'na', 'unknown', '-', 'none', ''):
                personal[current_field] = val
                if current_field.lower() in ('name', 'full name') and not current_person_name:
                    pass  # handled below
        current_field = None
        current_value_parts = []

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            _flush_field()
            continue

        # Check if this line is a "Field: Value" pattern
        m = _re.match(r'^([A-Za-z][A-Za-z\s/\(\)\.]{1,40}?)\s*[:\-]\s*(.+)$', line_stripped, _re.IGNORECASE)
        if m:
            field_raw = m.group(1).strip()
            value_raw = m.group(2).strip()
            field_lower = field_raw.lower().strip()

            # Skip non-personal fields
            if any(s in field_lower for s in skip_fields):
                _flush_field()
                continue

            # Flush previous field
            _flush_field()

            # Normalize field name
            field_name = _re.sub(r'\s+', ' ', field_raw).title()

            val = _clean(value_raw)
            if val and val.lower() not in ('nil', 'n/a', 'na', 'unknown', '-', 'none', ''):
                current_field = field_name
                current_value_parts = [val]

                # Track main person name
                if field_lower in ('name', 'full name', 'accused', 'victim', 'complainant') and not current_person_name:
                    current_person_name = _take_name(val)

        elif current_field and line_stripped and not line_stripped.startswith('#'):
            # Continuation of previous field value (e.g. multi-line address)
            current_value_parts.append(line_stripped)

    _flush_field()

    # ── Step 2: Extract family relationships ──────────────────────────────
    for line in lines:
        line = line.strip()
        if not line: continue

        for pat, relation in [
            (r'\bS/O\s+([A-Z][a-zA-Z\s@]{2,40})', 'father'),
            (r'\bD/O\s+([A-Z][a-zA-Z\s@]{2,40})', 'father'),
            (r'\bW/O\s+([A-Z][a-zA-Z\s@]{2,40})', 'husband'),
            (r'\bSon\s+of\s+([A-Z][a-zA-Z\s@]{2,40})', 'father'),
            (r'\bDaughter\s+of\s+([A-Z][a-zA-Z\s@]{2,40})', 'father'),
            (r'\bWife\s+of\s+([A-Z][a-zA-Z\s@]{2,40})', 'husband'),
            (r'\bBrother\s+of\s+([A-Z][a-zA-Z\s@]{2,40})', 'brother'),
            (r'\bSister\s+of\s+([A-Z][a-zA-Z\s@]{2,40})', 'sister'),
            (r'\bMother\s+of\s+([A-Z][a-zA-Z\s@]{2,40})', 'mother'),
            (r'\bFather\s+of\s+([A-Z][a-zA-Z\s@]{2,40})', 'father'),
            (r'^(?:Father|Papa|Pita)\s*[:\-]\s*(.+)', 'father'),
            (r'^(?:Mother|Maa|Mata)\s*[:\-]\s*(.+)', 'mother'),
            (r'^(?:Wife|Patni|Spouse)\s*[:\-]\s*(.+)', 'wife'),
            (r'^(?:Husband|Pati)\s*[:\-]\s*(.+)', 'husband'),
            (r'^(?:Brother|Bhai)\s*[:\-]\s*(.+)', 'brother'),
            (r'^(?:Sister|Behen)\s*[:\-]\s*(.+)', 'sister'),
            (r'^(?:Son|Beta)\s*[:\-]\s*(.+)', 'son'),
            (r'^(?:Daughter|Beti)\s*[:\-]\s*(.+)', 'daughter'),
            (r'^(?:Parentage)\s*[:\-]\s*(.+)', 'father'),
        ]:
            for m in _re.finditer(pat, line, _re.IGNORECASE):
                name = _take_name(m.group(1))
                if name and name.lower() not in seen:
                    seen.add(name.lower())
                    family.append({'name': name, 'relation': relation, 'gender': _guess_gender(name, relation), 'details': ''})

    # ── Step 3: Extract associates ────────────────────────────────────────
    for line in lines:
        line = line.strip()
        if not line: continue

        for pat, relation in [
            (r'\b(?:associate|associates)\s+(?:of\s+)?([A-Z][a-zA-Z\s@]{2,40})', 'associate'),
            (r'\b(?:gang\s+member|gang\s+associate)\s+([A-Z][a-zA-Z\s@]{2,40})', 'gang member'),
            (r'\b(?:friend|close\s+friend)\s+(?:of\s+)?([A-Z][a-zA-Z\s@]{2,40})', 'friend'),
            (r'\b(?:co-accused|co\s+accused)\s+([A-Z][a-zA-Z\s@]{2,40})', 'co-accused'),
            (r'\b(?:partner|accomplice)\s+(?:of\s+)?([A-Z][a-zA-Z\s@]{2,40})', 'accomplice'),
        ]:
            for m in _re.finditer(pat, line, _re.IGNORECASE):
                name = _take_name(m.group(1))
                if name and name.lower() not in seen:
                    seen.add(name.lower())
                    associates.append({'name': name, 'relation': relation, 'gender': _guess_gender(name, relation), 'details': ''})

    logger.info(f"[ProfileGraph] Regex extracted: {len(personal)} personal fields, {len(family)} family, {len(associates)} associates")
    logger.info(f"[ProfileGraph] Personal fields: {list(personal.keys())}")

    return {
        'personal': personal,
        'family': family,
        'associates': associates,
        'main_person': current_person_name or personal.get('Name', personal.get('Accused', personal.get('Victim', ''))),
    }

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

