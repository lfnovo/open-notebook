import re
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional

import fitz
import numpy as np

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("InfographicPipeline")

# ============================================================================
# 1. TEXT EXTRACTION
# ============================================================================
class TextExtractorService:
    def _extract_sync(self, file_path: str) -> str:
        logger.info(f"📖 Extracting text from: {file_path}")
        if file_path.lower().endswith('.pdf'):
            text_parts = []
            with fitz.open(file_path) as doc:
                for page in doc:
                    text_parts.append(page.get_text())
            combined = "\n".join(text_parts).strip()
            if len(combined) >= 50:
                return combined
            try:
                import easyocr
                from pdf2image import convert_from_path
                reader = easyocr.Reader(['en'], gpu=False)
                images = convert_from_path(file_path)
                results = []
                for img in images:
                    results.extend(reader.readtext(np.array(img), detail=0))
                return "\n".join(results)
            except Exception as e:
                logger.warning(f"EasyOCR fallback failed: {e}")
                return combined
        else:
            try:
                import easyocr
                reader = easyocr.Reader(['en'], gpu=False)
                return "\n".join(reader.readtext(file_path, detail=0))
            except Exception as e:
                logger.warning(f"EasyOCR failed: {e}")
                return ""

    async def extract_text_async(self, file_path: str) -> str:
        return await asyncio.to_thread(self._extract_sync, file_path)


# ============================================================================
# 2. TEXT CLEANING
# ============================================================================
class InfographicTextProcessor:
    def __init__(self):
        self.clean_patterns = [
            (re.compile(r' |&NBSP;', re.I), ' '),
            (re.compile(r'=+\s*PAGE\s*\d+\s*=+', re.I), ' '),
            (re.compile(r'(\w)\n(\w)'), r'\1 \2'),
            (re.compile(r'\n+'), '\n'),
            (re.compile(r'\s+'), ' '),
        ]

    def _sync_clean(self, text: str) -> str:
        if not text:
            return ""
        for pattern, replacement in self.clean_patterns:
            text = pattern.sub(replacement, text)
        return text.strip()

    async def clean_text(self, text: str) -> str:
        return await asyncio.to_thread(self._sync_clean, text)


# ============================================================================
# 3. LLM SERVICE — extracts dossier-style structured data
# ============================================================================
class InfographicLLMService:
    SYSTEM_PROMPT = """You are an expert intelligence analyst. Extract structured dossier data from the document.

Return ONLY valid JSON matching this EXACT schema — no markdown, no extra text:
{{
  "header": {{
    "title": "DOSSIER TITLE IN CAPS",
    "subtitle": "One sentence profile description."
  }},
  "left_column": [
    {{"icon": "person", "title": "DISTINCT PHYSICAL MARKERS", "description": "Physical details extracted from text."}},
    {{"icon": "calendar", "title": "PERSONAL BACKGROUND", "description": "Demographics, address, background."}},
    {{"icon": "chat", "title": "COMMUNICATION STYLE", "description": "Languages, habits, phrases used."}}
  ],
  "right_column": [
    {{"icon": "gun", "title": "MODUS OPERANDI", "description": "How they operate, methods used."}},
    {{"icon": "shield", "title": "AFFILIATIONS", "description": "Gang, group, or associate connections."}},
    {{"icon": "gavel", "title": "CURRENT LEGAL STATUS", "description": "Current custody, charges, status."}}
  ],
  "stat": {{
    "value": "9",
    "label": "Recorded FIRs"
  }},
  "cases": [
    {{"id": "FIR 113/2021", "status": "Judicial Custody", "charges": "Forgery & Conspiracy (419/468 IPC)"}},
    {{"id": "FIR 556/2021", "status": "Pending Investigation", "charges": "Extortion & Threatening (384/387 IPC)"}},
    {{"id": "FIR 40/2021", "status": "Pending Investigation", "charges": "Attempted Murder (307/304 IPC)"}}
  ]
}}

RULES:
1. Extract REAL data from the document — do not invent facts.
2. If a field has no data, write "Not available." as the description.
3. cases: extract up to 3 most important cases/records/events from the document.
4. stat.value: extract the most impactful single number from the document (count, amount, year, etc).
5. Keep descriptions concise — 1-2 sentences max.
6. title must be in UPPERCASE."""

    def __init__(self, llm):
        self.llm = llm
        self.chain = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("human", "Document text:\n\n{text}"),
        ]) | self.llm | JsonOutputParser()
        logger.info("InfographicLLMService initialized.")

    async def extract_dossier_async(self, text: str) -> Dict[str, Any]:
        logger.info("🎨 Extracting dossier structure with LLM...")
        return await self.chain.ainvoke({"text": text[:12000]})


# ============================================================================
# 4. HTML RENDERER — generates the dossier infographic as HTML string
# ============================================================================
class DossierHtmlRenderer:
    # Inline SVG icons keyed by name
    ICONS = {
        "person": '<svg viewBox="0 0 100 100" width="48" height="48"><circle cx="50" cy="32" r="18" fill="none" stroke="#64748b" stroke-width="6"/><path d="M20 90 C20 65 80 65 80 90" fill="none" stroke="#64748b" stroke-width="6" stroke-linecap="round"/><path d="M62 28 Q80 10 95 28 Q80 46 62 34 Z" fill="none" stroke="#94a3b8" stroke-width="3"/><circle cx="80" cy="32" r="4" fill="#b91c1c"/></svg>',
        "calendar": '<svg viewBox="0 0 100 100" width="48" height="48"><rect x="10" y="20" width="80" height="70" rx="8" fill="none" stroke="#64748b" stroke-width="6"/><path d="M10 42 L90 42" stroke="#64748b" stroke-width="5"/><rect x="28" y="8" width="8" height="20" rx="4" fill="#475569"/><rect x="64" y="8" width="8" height="20" rx="4" fill="#475569"/><rect x="25" y="55" width="12" height="12" rx="2" fill="#b91c1c"/><rect x="44" y="55" width="12" height="12" rx="2" fill="#475569"/><rect x="63" y="55" width="12" height="12" rx="2" fill="#475569"/><rect x="25" y="72" width="12" height="12" rx="2" fill="#475569"/><rect x="44" y="72" width="12" height="12" rx="2" fill="#475569"/></svg>',
        "chat": '<svg viewBox="0 0 100 100" width="48" height="48"><ellipse cx="38" cy="42" rx="28" ry="20" fill="#1e3a5f"/><path d="M18 55 L10 72 L28 60 Z" fill="#1e3a5f"/><circle cx="28" cy="42" r="3" fill="#fff"/><circle cx="38" cy="42" r="3" fill="#fff"/><circle cx="48" cy="42" r="3" fill="#fff"/><ellipse cx="65" cy="62" rx="22" ry="15" fill="#b91c1c"/><path d="M78 70 L88 82 L72 76 Z" fill="#b91c1c"/></svg>',
        "gun": '<svg viewBox="0 0 100 100" width="48" height="48"><rect x="8" y="38" width="55" height="18" rx="4" fill="#475569"/><rect x="55" y="30" width="30" height="10" rx="3" fill="#475569"/><rect x="30" y="56" width="20" height="22" rx="4" fill="#334155"/><rect x="8" y="44" width="10" height="6" rx="2" fill="#64748b"/><circle cx="78" cy="35" r="5" fill="#b91c1c"/></svg>',
        "shield": '<svg viewBox="0 0 100 100" width="48" height="48"><path d="M50 8 L85 22 L85 52 C85 72 50 92 50 92 C50 92 15 72 15 52 L15 22 Z" fill="none" stroke="#1e3a5f" stroke-width="6"/><circle cx="50" cy="52" r="18" fill="#b91c1c"/><path d="M40 52 Q50 42 60 52 M40 52 Q50 62 60 52" fill="none" stroke="#fff" stroke-width="3"/></svg>',
        "gavel": '<svg viewBox="0 0 100 100" width="48" height="48"><rect x="10" y="60" width="55" height="12" rx="4" fill="#475569" transform="rotate(-45 37 66)"/><rect x="45" y="15" width="40" height="22" rx="5" fill="#5b4b6b" transform="rotate(-45 65 26)"/><rect x="15" y="72" width="70" height="8" rx="4" fill="#334155"/></svg>',
    }

    CASE_COLORS = ["#3b6fa0", "#9b3a3a", "#4a7c59"]

    def _esc(self, s: str) -> str:
        """HTML-escape a string."""
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    def _col_block(self, item: dict) -> str:
        icon_key = item.get("icon", "person")
        icon_svg = self.ICONS.get(icon_key, self.ICONS["person"])
        title = self._esc(item.get("title", ""))
        desc = self._esc(item.get("description", ""))
        return f"""
        <div class="info-block">
          <div class="info-icon">{icon_svg}</div>
          <div class="info-text">
            <div class="info-title">{title}</div>
            <div class="info-desc">{desc}</div>
          </div>
        </div>"""

    def _case_card(self, case: dict, idx: int) -> str:
        color = self.CASE_COLORS[idx % len(self.CASE_COLORS)]
        case_id = self._esc(case.get("id", f"Record {idx+1}"))
        status = self._esc(case.get("status", ""))
        charges = self._esc(case.get("charges", ""))
        status_html = f'<div class="card-subtitle">({status})</div>' if status else ""
        return f"""
        <div class="event-card">
          <div class="card-header" style="background:{color}">
            <div class="card-title">{case_id}</div>
            {status_html}
          </div>
          <div class="card-body">
            <span class="charges-label">Charges:</span> {charges}
          </div>
        </div>"""

    def render(self, data: dict) -> str:
        header = data.get("header", {})
        if isinstance(header, str):
            header = {"title": "SUBJECT DOSSIER", "subtitle": header}

        title = self._esc(header.get("title", "SUBJECT DOSSIER"))
        subtitle = self._esc(header.get("subtitle", ""))

        left_col = data.get("left_column", [])
        right_col = data.get("right_column", [])
        stat = data.get("stat", {})
        cases = data.get("cases", [])

        # Ensure lists
        if isinstance(left_col, dict):
            left_col = [{"icon": k, "title": k.upper(), "description": v} for k, v in left_col.items()]
        if isinstance(right_col, dict):
            right_col = [{"icon": k, "title": k.upper(), "description": v} for k, v in right_col.items()]

        left_html = "".join(self._col_block(item) for item in left_col[:3])
        right_html = "".join(self._col_block(item) for item in right_col[:3])
        cases_html = "".join(self._case_card(c, i) for i, c in enumerate(cases[:3]))

        stat_value = self._esc(str(stat.get("value", "")))
        stat_label = self._esc(stat.get("label", ""))

        # Stat block inside right column (replaces last item if stat exists)
        stat_block = ""
        if stat_value:
            stat_block = f"""
        <div class="stat-block">
          <div class="stat-number">{stat_value}</div>
          <div class="stat-label">{stat_label}</div>
        </div>"""

        avatar_svg = """<svg viewBox="0 0 200 260" width="220" height="280" xmlns="http://www.w3.org/2000/svg">
          <path d="M100 20 C60 20 40 55 40 95 C40 135 68 148 70 165 C22 175 5 210 5 255 L195 255 C195 210 178 175 130 165 C132 148 160 135 160 95 C160 55 140 20 100 20 Z" fill="none" stroke="#cbd5e1" stroke-width="6" stroke-linejoin="round"/>
          <path d="M100 20 C60 20 40 55 40 95 C40 135 68 148 70 165 C22 175 5 210 5 255 L100 255 Z" fill="#1e3a5f" opacity="0.85"/>
          <path d="M100 20 C140 20 160 55 160 95 C160 135 132 148 130 165 C178 175 195 210 195 255 L100 255 Z" fill="#b91c1c" opacity="0.85"/>
          <path d="M100 24 C64 24 44 57 44 95 C44 133 70 146 72 162 C26 172 10 207 10 255 L190 255 C190 207 174 172 128 162 C130 146 156 133 156 95 C156 57 136 24 100 24 Z" fill="#f0f4f8"/>
          <circle cx="100" cy="88" r="28" fill="#e2e8f0" stroke="#cbd5e1" stroke-width="3"/>
          <ellipse cx="100" cy="82" rx="14" ry="16" fill="#94a3b8"/>
          <path d="M72 108 C72 95 128 95 128 108" fill="#94a3b8"/>
        </svg>"""

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Segoe UI', Arial, sans-serif;
    background: linear-gradient(135deg, #f0f4f8 0%, #e2e8f0 100%);
    color: #0f172a;
    padding: 32px 40px 28px;
    min-height: 100vh;
  }}
  .header {{ margin-bottom: 22px; }}
  .header h1 {{
    font-size: 36px; font-weight: 900; color: #1e3a5f;
    text-transform: uppercase; letter-spacing: -0.5px; line-height: 1.1;
  }}
  .header h1 span {{ color: #b91c1c; }}
  .header p {{ font-size: 14px; color: #475569; margin-top: 6px; max-width: 700px; line-height: 1.5; }}

  .main-layout {{
    display: grid;
    grid-template-columns: 1fr 220px 1fr;
    gap: 24px;
    align-items: center;
    margin-bottom: 28px;
  }}
  .col {{ display: flex; flex-direction: column; gap: 24px; }}
  .col-labels {{
    display: flex; flex-direction: column; align-items: center; gap: 8px;
  }}
  .col-label {{
    font-size: 11px; font-weight: 900; text-transform: uppercase;
    letter-spacing: 1px; color: #1e3a5f; text-align: center; line-height: 1.3;
  }}

  .info-block {{ display: flex; gap: 12px; align-items: flex-start; }}
  .info-icon {{ width: 48px; height: 48px; flex-shrink: 0; }}
  .info-title {{
    font-size: 11px; font-weight: 900; text-transform: uppercase;
    color: #0f172a; letter-spacing: 0.5px; margin-bottom: 3px;
  }}
  .info-desc {{ font-size: 12px; color: #334155; line-height: 1.45; }}

  .stat-block {{
    display: flex; flex-direction: column; align-items: flex-start; gap: 2px;
    padding: 8px 0;
  }}
  .stat-number {{
    font-size: 52px; font-weight: 900; color: #5b4b6b; line-height: 1;
  }}
  .stat-label {{ font-size: 11px; color: #475569; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}

  .section-title {{
    font-size: 14px; font-weight: 900; color: #1e3a5f;
    text-transform: uppercase; letter-spacing: 0.5px;
    margin-bottom: 14px;
    display: flex; align-items: center; gap: 10px;
  }}
  .section-title::after {{
    content: ''; flex: 1; height: 2px; background: #cbd5e1;
  }}

  .cards-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
  }}
  .event-card {{
    background: #fff;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    border: 1px solid #e2e8f0;
    display: flex; flex-direction: column;
  }}
  .card-header {{
    padding: 10px 14px; color: #fff;
    display: flex; flex-direction: column; gap: 2px;
  }}
  .card-title {{ font-size: 14px; font-weight: 900; }}
  .card-subtitle {{ font-size: 11px; font-weight: 600; opacity: 0.9; }}
  .card-body {{
    padding: 12px 14px; font-size: 12px; color: #334155;
    font-weight: 500; line-height: 1.45; background: #fafafa; flex: 1;
  }}
  .charges-label {{ font-weight: 700; color: #0f172a; }}
</style>
</head>
<body>
  <div class="header">
    <h1>{title}</h1>
    <p>{subtitle}</p>
  </div>

  <div class="main-layout">
    <!-- Left column -->
    <div class="col">{left_html}</div>

    <!-- Center avatar -->
    <div class="col-labels">
      <div class="col-label">Subject<br>Identification<br>&amp; Physicals</div>
      {avatar_svg}
      <div class="col-label">Criminal<br>Profile<br>&amp; History</div>
    </div>

    <!-- Right column -->
    <div class="col">
      {right_html}
      {stat_block}
    </div>
  </div>

  <div class="section-title">Recent Legal Involvements</div>
  <div class="cards-grid">{cases_html}</div>
</body>
</html>"""


# ============================================================================
# 5. PIPELINE
# ============================================================================
class InfographicPipeline:
    def __init__(
        self,
        extractor: TextExtractorService,
        processor: InfographicTextProcessor,
        llm_service: InfographicLLMService,
        renderer: Optional[DossierHtmlRenderer] = None,
    ):
        self.extractor = extractor
        self.processor = processor
        self.llm_service = llm_service
        self.renderer = renderer or DossierHtmlRenderer()

    async def generate_from_source_id(self, source_id: str) -> Dict[str, Any]:
        from open_notebook.domain.notebook import Source

        logger.info(f"🚀 Starting Infographic Generation for Source ID: {source_id}")

        source = await Source.get(source_id)
        if not source:
            return self._fallback("Unknown Source", "Source not found.")

        full_text = ""
        if source.full_text and source.full_text.strip():
            full_text = source.full_text
        elif source.asset and source.asset.file_path:
            full_text = await self.extractor.extract_text_async(source.asset.file_path)

        if not full_text:
            return self._fallback(source.title or "Unknown Source", "No text content found.")

        clean_text = await self.processor.clean_text(full_text)
        data = await self.llm_service.extract_dossier_async(clean_text)

        html = self.renderer.render(data)
        data["html"] = html
        data["source_id"] = source_id
        logger.info(f"✅ Infographic generated for source_id: {source_id}")
        return data

    def _fallback(self, title: str, message: str) -> Dict[str, Any]:
        renderer = DossierHtmlRenderer()
        fallback_data = {
            "header": {"title": title.upper(), "subtitle": message},
            "left_column": [],
            "right_column": [],
            "stat": {},
            "cases": [],
        }
        return {
            "title": title,
            "subtitle": message,
            "html": renderer.render(fallback_data),
            "sections": [],
        }
