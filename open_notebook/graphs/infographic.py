import re
import json
import logging
import asyncio
import concurrent.futures
import os
from typing import Dict, Any, List, Optional

import fitz
import numpy as np

from langchain_core.prompts import ChatPromptTemplate

# --- Kafka Imports ---
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

# -------------------------------------------------
# LOGGER
# -------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("InfographicPipeline")

# ============================================================================
# 1. TEXT EXTRACTION
# ============================================================================
class TextExtractorService:
    def _ocr_image_bytes(self, image_bytes: bytes, reader) -> str:
        """Run EasyOCR on raw PNG bytes from a rasterised page."""
        try:
            import io as _io
            from PIL import Image as _Image
            img = _Image.open(_io.BytesIO(image_bytes)).convert("RGB")
            lines = reader.readtext(np.array(img), detail=0, batch_size=4)
            return " ".join(lines).strip()
        except Exception as e:
            logger.warning(f"OCR on image bytes failed: {e}")
            return ""

    def _extract_sync(self, file_path: str) -> str:
        """
        Extract text from a file.
        For PDFs: per-page embedded text + per-page OCR fallback when sparse (< 200 chars).
        For images: direct EasyOCR.
        """
        logger.info(f"Extracting text from: {file_path}")
        if file_path.lower().endswith('.pdf'):
            try:
                import easyocr
                reader = easyocr.Reader(['en', 'hi'], gpu=False, verbose=False)
            except Exception as e:
                logger.warning(f"EasyOCR init failed: {e}")
                reader = None

            final_pages: list[str] = []
            try:
                doc = fitz.open(file_path)
            except Exception as e:
                logger.warning(f"PyMuPDF could not open '{file_path}': {e}")
                return ""

            for page_index, page in enumerate(doc):
                page_text_parts: list[str] = []

                # 1. Embedded text
                try:
                    embedded = page.get_text("text").strip()
                    if embedded:
                        page_text_parts.append(embedded)
                except Exception:
                    pass

                # 2. Text blocks (captures table cells and structured content)
                try:
                    blocks = page.get_text("blocks")
                    for block in blocks:
                        if block[6] == 0 and block[4].strip():
                            page_text_parts.append(block[4].strip())
                except Exception:
                    pass

                combined = "\n".join(page_text_parts).strip()

                # 3. Per-page OCR if text is sparse (scanned / image-based page)
                if len(combined) < 200 and reader is not None:
                    try:
                        pix = page.get_pixmap(dpi=300)
                        img_bytes = pix.tobytes("png")
                        ocr_text = self._ocr_image_bytes(img_bytes, reader)
                        if ocr_text:
                            logger.info(f"Page {page_index + 1}: OCR extracted {len(ocr_text)} chars")
                            page_text_parts.append("[OCR PAGE CONTENT]\n" + ocr_text)
                    except Exception as e:
                        logger.warning(f"Page {page_index + 1} OCR failed: {e}")

                # Deduplicate parts while preserving order
                final_pages.append("\n".join(dict.fromkeys(page_text_parts)))

            doc.close()
            return "\n\n".join(final_pages).strip()
        else:
            try:
                import easyocr
                reader = easyocr.Reader(['en'], gpu=False, verbose=False)
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
# 3. LLM SERVICE — Universal Infographic Data Extractor
# ============================================================================
class InfographicLLMService:
    SYSTEM_PROMPT = """You are an expert information designer. Your task is to read ANY document and extract its key information into a structured JSON format for rendering as a visual infographic.

RULES:
- Use ONLY information explicitly present in the document. Do NOT invent, assume, or hallucinate any data.
- Every field must be populated with real content from the document.
- If a field has no matching data, use the most relevant available fact instead of leaving it empty.
- The output must be valid JSON only — no markdown fences, no commentary, no extra text.

STEP 1 — UNDERSTAND THE DOCUMENT
Read the full document and identify: the main subject, domain (e.g. research, business, legal, medical, technical, biographical, news, educational), and the most important facts, figures, and themes.

STEP 2 — BUILD THE JSON
Fill every field below using real data from the document:

{
  "header": {
    "title": "SHORT UPPERCASE TITLE DESCRIBING THE DOCUMENT SUBJECT (max 8 words)",
    "subtitle": "One or two sentences summarising the document's core content and purpose, using specific facts.",
    "center_icon": "Pick the single best icon for the domain: user | building | shield | activity | finance | law | medical | briefcase | document | education | chart | network"
  },
  "left_column": [
    {
      "icon": "info",
      "title": "FIRST KEY CATEGORY (e.g. Overview, Background, Objective, Profile)",
      "description": "2-4 sentences of specific facts, names, dates, or figures from the document."
    },
    {
      "icon": "calendar",
      "title": "SECOND KEY CATEGORY (e.g. Timeline, History, Key Dates, Milestones)",
      "description": "2-4 sentences of specific facts from the document."
    },
    {
      "icon": "target",
      "title": "THIRD KEY CATEGORY (e.g. Goals, Scope, Focus Area, Methodology)",
      "description": "2-4 sentences of specific facts from the document."
    }
  ],
  "right_column": [
    {
      "icon": "briefcase",
      "title": "FOURTH KEY CATEGORY (e.g. Results, Findings, Outcomes, Products)",
      "description": "2-4 sentences of specific facts from the document."
    },
    {
      "icon": "alert",
      "title": "FIFTH KEY CATEGORY (e.g. Risks, Challenges, Issues, Limitations)",
      "description": "2-4 sentences of specific facts from the document."
    },
    {
      "icon": "network",
      "title": "SIXTH KEY CATEGORY (e.g. Stakeholders, Connections, Relationships, Impact)",
      "description": "2-4 sentences of specific facts from the document."
    }
  ],
  "stat": {
    "value": "The single most important number, figure, or metric from the document (e.g. $4.2M, 87%, 12 years, 3 phases)",
    "label": "Short label explaining what that number represents (e.g. Total Budget, Success Rate, Project Duration)"
  },
  "highlights": [
    {
      "title": "FIRST KEY FINDING OR EVENT (uppercase, max 6 words)",
      "subtitle": "Date, category, or source reference if available",
      "description": "3-5 sentences with specific details, quotes, or data points from the document."
    },
    {
      "title": "SECOND KEY FINDING OR EVENT",
      "subtitle": "Date, category, or source reference if available",
      "description": "3-5 sentences with specific details from the document."
    },
    {
      "title": "THIRD KEY FINDING OR EVENT",
      "subtitle": "Date, category, or source reference if available",
      "description": "3-5 sentences with specific details from the document."
    }
  ]
}

ICON OPTIONS for columns: user, calendar, info, target, chart, briefcase, shield, lightbulb, document, activity, alert, building, timeline, family, network, group, location, law, crime, finance, medical, education.

Choose category titles and icons that best match the actual content of the document — do not use generic placeholders.
"""

    def __init__(self, llm):
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("human", (
                "Read the following document carefully and extract ALL key information into the JSON infographic structure.\n"
                "Use specific facts, names, numbers, and dates from the document — do not use placeholders.\n"
                "Return ONLY the JSON object, nothing else.\n\n"
                "DOCUMENT:\n{text}"
            )),
        ])
        logger.info("InfographicLLMService initialized.")

    async def extract_dossier_async(self, text: str) -> Dict[str, Any]:
        logger.info("Extracting universal infographic structure with LLM...")
        messages = self.prompt.format_messages(text=text[:20000])
        logger.info("Calling llm.ainvoke...")
        response = await self.llm.ainvoke(messages)
        raw = response.content if hasattr(response, "content") else str(response)
        logger.info("llm.ainvoke completed. Parsing response...")

        # Strip any wrapper tags the model may add
        raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL)
        raw = re.sub(r'<answer>(.*?)</answer>', r'\1', raw, flags=re.DOTALL)
        raw = raw.strip()

        # Strip markdown fences
        fence = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
        candidate = fence.group(1) if fence else raw

        # Extract outermost JSON object
        brace = re.search(r'\{.*\}', candidate, re.DOTALL)
        if brace:
            try:
                result = json.loads(brace.group())
                logger.info("JSON parsed successfully.")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse failed: {e}")

        logger.error("Could not extract JSON from LLM output — returning empty dict")
        return {}



# ============================================================================
# 4. PIPELINE
# ============================================================================
class InfographicPipeline:
    def __init__(
        self,
        extractor: TextExtractorService,
        processor: InfographicTextProcessor,
        llm_service: InfographicLLMService,
    ):
        self.extractor = extractor
        self.processor = processor
        self.llm_service = llm_service

    async def generate_from_source_id(self, source_id: str) -> Dict[str, Any]:
        from open_notebook.domain.notebook import Source

        logger.info(f"Starting Infographic Generation for Source ID: {source_id}")

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
        logger.info("Text cleaned. Calling LLM...")
        data = await self.llm_service.extract_dossier_async(clean_text)
        logger.info("LLM completed.")

        data["source_id"] = source_id
        logger.info(f"Infographic generated successfully for source_id: {source_id}")
        return data

    def _fallback(self, title: str, message: str) -> Dict[str, Any]:
        return {
            "source_id": "",
            "header": {"title": title.upper(), "subtitle": message},
            "left_column": [], "right_column": [], "stat": {}, "highlights": [],
        }


# ============================================================================
# 6. KAFKA ORCHESTRATOR LAYER (Distributed Processing)
# ============================================================================
class KafkaInfographicOrchestrator:
    """
    Wraps InfographicPipeline with Kafka Producer/Consumer logic.
    The consumer is for tracking/async results only — the HTTP endpoint
    runs the pipeline directly to avoid double execution.
    """

    def __init__(
        self,
        pipeline: Optional[InfographicPipeline],
        bootstrap_servers: str = None,
        input_topic: str = "infographic_jobs",
        output_topic: str = "infographic_results",
        group_id: str = "infographic_worker_group",
    ):
        self.pipeline = pipeline
        self.bootstrap_servers = bootstrap_servers or os.environ.get(
            "KAFKA_BOOTSTRAP_SERVERS", "kafka:9093"
        )
        self.input_topic = input_topic
        self.output_topic = output_topic
        self.group_id = group_id

    async def produce_jobs(self, source_ids: List[str]):
        """Publish infographic job tracking events to Kafka (fire-and-forget)."""
        producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers)
        await producer.start()
        logger.info(f"Kafka Infographic Producer: sending {len(source_ids)} tracking events...")
        try:
            for sid in source_ids:
                payload = json.dumps({"source_id": sid, "status": "started"}).encode("utf-8")
                await producer.send_and_wait(self.input_topic, payload)
        except Exception as e:
            logger.error(f"Failed to produce infographic Kafka messages: {e}")
        finally:
            await producer.stop()

    async def _send_result(self, producer, source_id: str, result: Dict[str, Any], status: str):
        payload = json.dumps(
            {"source_id": source_id, "status": status, "data": result}
        ).encode("utf-8")
        await producer.send_and_wait(self.output_topic, payload)

    async def start_consumer(self, max_concurrent: int = 3):
        """
        Consume tracking events from Kafka.
        NOTE: Does NOT re-run the pipeline — the HTTP endpoint handles execution.
        This consumer only logs/tracks job events. No output topic needed.
        """
        consumer = AIOKafkaConsumer(
            self.input_topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset="latest",  # Only process new messages, not backlog
        )

        await consumer.start()
        logger.info(f"Kafka Infographic Consumer listening on topic '{self.input_topic}' (tracking only)...")

        async def process_message(msg):
            try:
                payload = json.loads(msg.value.decode("utf-8"))
                source_id = payload.get("source_id")
                status = payload.get("status", "unknown")
                logger.info(f"Kafka tracking event: source_id={source_id}, status={status}")
            except Exception as e:
                logger.error(f"Kafka tracking message error: {e}")

        try:
            async for msg in consumer:
                asyncio.create_task(process_message(msg))
        finally:
            await consumer.stop()
            logger.info("Kafka Infographic Consumer stopped.")

    async def _send_result(self, producer, source_id: str, result: Dict[str, Any], status: str):
        """No-op: output topic removed to avoid 'topic not found' errors."""
        pass
