import re
import json
import logging
import asyncio
import concurrent.futures
from typing import Dict, Any, List, Optional
from collections import Counter, defaultdict

import easyocr
import nltk
import spacy
import fitz
from pdf2image import convert_from_path
import numpy as np

from spacy.matcher import Matcher

# --- Kafka Imports ---
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.messages import HumanMessage

# Ensure NLTK models are available
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('averaged_perceptron_tagger_eng', quiet=True)
nltk.download('maxent_ne_chunker', quiet=True)
nltk.download('maxent_ne_chunker_tab', quiet=True)
nltk.download('words', quiet=True)

# -------------------------------------------------
# LOGGER
# -------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MindMapPipeline")

# ============================================================================
# 1. OCR LAYER (Multithreaded EasyOCR Extraction)
# ============================================================================
class EasyOCRService:
    def __init__(self, langs: List[str] = ['en'], max_threads: int = 4):
        logger.info("Loading EasyOCR models...")
        self.reader = easyocr.Reader(langs, gpu=False)
        self.max_threads = max_threads

    def _extract_sync(self, file_path: str) -> str:
        logger.info(f"Extracting text from: {file_path}")
        if file_path.lower().endswith('.pdf'):
            text_results = []
            with fitz.open(file_path) as doc:
                for page in doc:
                    text_results.append(page.get_text())
            combined_text = "\n".join(text_results).strip()
            if len(combined_text) < 50:
                logger.info("PDF looks like a scanned image. Using MULTITHREADED OCR...")
                images = convert_from_path(file_path)
                def process_image(img):
                    return self.reader.readtext(np.array(img), detail=0, batch_size=4)
                ocr_results = []
                workers = min(self.max_threads, len(images)) if images else 1
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                    results = list(executor.map(process_image, images))
                    for res in results:
                        ocr_results.extend(res)
                return "\n".join(ocr_results)
            return combined_text
        else:
            return "\n".join(self.reader.readtext(file_path, detail=0))

    async def extract_text_async(self, file_path: str) -> str:
        return await asyncio.to_thread(self._extract_sync, file_path)


# ============================================================================
# 2. TEXT PROCESSING LAYER (Optimized NLP)
# ============================================================================
class TextProcessor:
    def __init__(self, nlp_model_name: str = "en_core_web_sm"):
        try:
            import pytextrank  # noqa: F401
            self.nlp = spacy.load(nlp_model_name, disable=["textcat"])
            self.nlp.add_pipe("textrank")
        except OSError:
            logger.error(f"spaCy model '{nlp_model_name}' not found. Run: python -m spacy download {nlp_model_name}")
            raise

        self.clean_patterns = [
            (re.compile(r' |&NBSP;', re.I), ' '),
            (re.compile(r'=+\s*PAGE\s*\d+\s*=+', re.I), ' '),
            (re.compile(r'\b\d+\.\b'), ' '),
            (re.compile(r'(\w)\n(\w)'), r'\1 \2'),
            (re.compile(r'\n+'), '\n'),
            (re.compile(r'\s+'), ' '),
        ]
        self.bad_name_keywords = {
            "police", "officer", "court", "station", "security", "type",
            "status", "alias", "dossier", "unknown", "fir", "act"
        }

    def _sync_clean(self, text: str) -> str:
        if not text:
            return ""
        for pattern, replacement in self.clean_patterns:
            text = pattern.sub(replacement, text)
        return text.strip()

    async def clean_ocr_text(self, text: str) -> str:
        return await asyncio.to_thread(self._sync_clean, text)

    def _sync_detect_person(self, text: str) -> str:
        logger.info("NLP performing Named Entity Extraction...")
        processed_text = text.title()
        self.nlp.max_length = max(len(processed_text) + 100, 1000000)
        doc = self.nlp(processed_text)

        candidates = []
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                clean_name = ent.text.strip()
                if 2 < len(clean_name) < 25 and not any(bad in clean_name.lower() for bad in self.bad_name_keywords):
                    candidates.append(clean_name)

        name_matches = re.findall(r'\bName\b[\s\:\-]+([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,2})', processed_text)
        for match in name_matches:
            if len(match) > 2 and not any(bad in match.lower() for bad in self.bad_name_keywords):
                candidates.append(match.strip())

        if not candidates:
            logger.warning("NLP could not find a person's name. Defaulting to 'Target Subject'.")
            return "Target Subject"

        name_counts = Counter(candidates)
        best_name = "Target Subject"
        best_score = -999

        for name, count in name_counts.items():
            word_count = len(name.split())
            score = count
            if word_count == 2:
                score += 3
            elif word_count == 3:
                score += 1
            if word_count > 4 or len(name) < 3:
                score -= 10
            if score > best_score:
                best_score = score
                best_name = name

        winner = name_counts.most_common(1)[0][0] if best_score < -5 else best_name
        logger.info(f"NLP Extracted Name: {winner}")
        return winner

    async def detect_main_person_async(self, text: str) -> Optional[str]:
        return await asyncio.to_thread(self._sync_detect_person, text)

    @staticmethod
    def deduplicate_facts(facts: List[str]) -> List[str]:
        seen = set()
        clean = []
        for f in facts:
            key = re.sub(r"\W+", "", f.lower())
            if key not in seen:
                seen.add(key)
                clean.append(f.strip())
        return clean


# ============================================================================
# 3. LLM SERVICE LAYER (Prompts & Invocation)
# ============================================================================
class IntelligenceLLMService:
    """Manages LangChain prompts and LLM interactions asynchronously."""

    def __init__(self, llm):
        self.llm = llm

        self.fact_system_prompt = """You are an expert intelligence analyst extracting hard, undeniable facts from noisy OCR document text.
Strictly obey the following rules:
1. Extract ONLY information explicitly stated in the text.
2. Prioritize names, physical descriptions, dates, locations, and criminal records.
3. Write each fact as a single, complete standalone sentence.
4. CRITICAL: Return ONLY a valid JSON array of strings. Do not add conversational text.

EXAMPLE OUTPUT:
["The subject's name is Ankit Lagarpur.", "He is associated with the Kala Jathedi Gang.", "His height is 167 cm."]
"""
        logger.info("Fact Chain Initialized...")
        self.fact_chain = ChatPromptTemplate.from_messages([
            ("system", self.fact_system_prompt),
            ("human", "Document Text to Analyze:\n\n{context}")
        ]) | self.llm | StrOutputParser()

        logger.info("Mind Map Chain Initialized...")
        self.mindmap_chain = ChatPromptTemplate.from_messages([
            ("system", """You are an expert information architect creating a logically structured JSON mind map from the provided document data.

HIERARCHY RULES:
1. Root (Level 0): Use a concise, highly descriptive title representing the main subject of the document as the Root label.
2. Categories (Level 1): Dynamically extract the most logical main themes, sections, or categories based entirely on the provided context.
3. Sub-Categories (Level 2+): Where appropriate, create sub-categories to logically group related information.
4. Facts (Leaf Nodes): Represent actual data points as concise strings. Use 'Key: Value' format where appropriate.

OUTPUT FORMAT (Return ONLY valid JSON matching this recursive schema exactly):
{{
  "label": "Main Subject Title",
  "children": [
    {{
      "label": "Dynamic Category 1",
      "children": [
        {{ "label": "Key: Value or concise fact" }},
        {{ "label": "Another relevant detail" }}
      ]
    }},
    {{
      "label": "Dynamic Category 2",
      "children": [
        {{
          "label": "Dynamic Sub-Category",
          "children": [
            {{ "label": "Detailed point 1" }},
            {{ "label": "Detailed point 2" }}
          ]
        }}
      ]
    }}
  ]
}}"""),
            ("human", "Primary Subject/Topic: {subject}\n\nDocument Context/Data:\n{context}")
        ]) | self.llm | JsonOutputParser()

    def extract_facts_sync(self, text_chunk: str) -> List[str]:
        """Synchronous version to support the concurrent ThreadPoolExecutor pipeline."""
        try:
            raw_response = self.fact_chain.invoke({"context": text_chunk})
            raw_facts = raw_response.strip().removeprefix("```json").removesuffix("```").strip()
            parsed = json.loads(raw_facts)
            extracted = []
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, str):
                        extracted.append(item)
                    elif isinstance(item, dict) and "fact" in item:
                        extracted.append(str(item["fact"]))
            return extracted
        except Exception as e:
            logger.warning(f"Fact extraction parsing failed, skipping chunk. Error: {e}")
            return []

    async def extract_facts_async(self, text_chunk: str, images_b64: Optional[List[str]] = None) -> List[str]:
        try:
            message_content = [{"type": "text", "text": f"Document Text to Analyze:\n\n{text_chunk[:10000]}"}]
            if images_b64:
                for img_data in images_b64:
                    message_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}
                    })
            human_message = HumanMessage(content=message_content)
            raw_response = await self.llm.ainvoke([
                {"role": "system", "content": self.fact_system_prompt},
                human_message
            ])
            parser = StrOutputParser()
            raw_facts = parser.invoke(raw_response)
            raw_facts = raw_facts.strip().removeprefix("```json").removesuffix("```").strip()
            parsed = json.loads(raw_facts)
            extracted = []
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, str):
                        extracted.append(item)
                    elif isinstance(item, dict) and "fact" in item:
                        extracted.append(str(item["fact"]))
            return extracted
        except Exception as e:
            logger.warning(f"Fact extraction parsing failed, skipping chunk. Error: {e}")
            return []

    async def generate_mind_map_async(self, person: str, facts: List[str]) -> Dict:
        result = await self.mindmap_chain.ainvoke({
            "subject": person,
            "context": json.dumps(facts, indent=2)
        })
        return result


# ============================================================================
# 4. PIPELINE LAYER
# ============================================================================
class MindMapPipeline:
    """Coordinates Local Data Fetching -> NLP Processing -> LLM Execution."""

    def __init__(self, ocr_service: EasyOCRService, processor: TextProcessor, llm_service: IntelligenceLLMService):
        self.ocr_service = ocr_service
        self.processor = processor
        self.llm_service = llm_service

    async def generate_from_source_id(self, source_id: str) -> Dict:
        """Fetches the source by ID, extracts/gets text, and generates the mind map."""
        from open_notebook.domain.notebook import Source

        logger.info(f"Starting Mind Map Generation for Source ID: {source_id}")

        source = await Source.get(source_id)
        if not source:
            logger.error(f"Source not found for id: {source_id}")
            return {"label": "Target Subject", "children": [{"label": "Source not found."}]}

        full_text = ""
        if source.full_text and source.full_text.strip():
            logger.info("Using extracted text from database.")
            full_text = source.full_text
        elif source.asset and source.asset.file_path:
            logger.info("No text in DB, performing OCR on file...")
            full_text = await self.ocr_service.extract_text_async(source.asset.file_path)

        if not full_text:
            return {"label": "Target Subject", "children": [{"label": "No data/text found to process."}]}

        clean_text = await self.processor.clean_ocr_text(full_text)
        main_person = await self.processor.detect_main_person_async(clean_text) or "Target Subject"

        text_chunks = [clean_text[i:i+10000] for i in range(0, len(clean_text), 10000)]
        all_facts = []

        logger.info(f"Extracting facts across {len(text_chunks)} chunks concurrently...")
        tasks = [asyncio.to_thread(self.llm_service.extract_facts_sync, chunk) for chunk in text_chunks]
        chunk_results = await asyncio.gather(*tasks)

        for result in chunk_results:
            if isinstance(result, list):
                all_facts.extend(result)

        facts = self.processor.deduplicate_facts(all_facts)
        if not facts:
            return {"label": f"{main_person} Dossier", "children": [{"label": "No extractable facts found."}]}

        result = await self.llm_service.generate_mind_map_async(main_person, facts)
        logger.info(f"Mind map generation completed for source_id: {source_id}")
        return result

    def _fallback_mind_map(self, person: str, facts: List[str]) -> Dict:
        buckets = defaultdict(list)
        for fact in facts:
            f = fact.lower()
            if any(k in f for k in ["resident", "born", "age"]):
                buckets["Identity & Background"].append(fact)
            elif any(k in f for k in ["fir", "arrest", "crime", "case"]):
                buckets["Criminal History"].append(fact)
            else:
                buckets["Other Details"].append(fact)
        return {
            "label": person,
            "children": [{"label": k, "children": [{"label": f} for f in v]} for k, v in buckets.items() if v]
        }


# ============================================================================
# 5. KAFKA ORCHESTRATOR LAYER (Distributed Processing)
# ============================================================================
class KafkaMindMapOrchestrator:
    """
    Wraps the MindMapPipeline with Kafka Producer and Consumer logic.
    """

    def __init__(
        self,
        pipeline: Optional[MindMapPipeline],
        bootstrap_servers: str = None,
        input_topic: str = 'mindmap_jobs',
        output_topic: str = 'mindmap_results',
        group_id: str = 'mindmap_worker_group'
    ):
        import os
        self.pipeline = pipeline
        self.bootstrap_servers = bootstrap_servers or os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9093")
        self.input_topic = input_topic
        self.output_topic = output_topic
        self.group_id = group_id

    async def produce_jobs(self, source_ids: List[str]):
        """Produces source processing jobs to the Kafka input topic."""
        producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers)
        await producer.start()
        logger.info(f"Kafka Producer: sending {len(source_ids)} jobs...")
        try:
            for sid in source_ids:
                payload = json.dumps({"source_id": sid}).encode('utf-8')
                await producer.send_and_wait(self.input_topic, payload)
                logger.info(f"Published job for source_id: {sid}")
        except Exception as e:
            logger.error(f"Failed to produce Kafka messages: {e}")
        finally:
            await producer.stop()
            logger.info("Kafka Producer stopped.")

    async def _send_result(self, producer: AIOKafkaProducer, source_id: str, result: Dict[str, Any], status: str):
        """Helper to send the final mind map back to an output topic."""
        payload = json.dumps({"source_id": source_id, "status": status, "data": result}).encode('utf-8')
        await producer.send_and_wait(self.output_topic, payload)

    async def start_consumer(self, max_concurrent: int = 3):
        """
        Consumes jobs from Kafka and processes them concurrently up to a strict limit.
        """
        consumer = AIOKafkaConsumer(
            self.input_topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset='latest'
        )
        producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers)

        await consumer.start()
        await producer.start()

        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_message(msg):
            async with semaphore:
                payload = json.loads(msg.value.decode('utf-8'))
                source_id = payload.get("source_id")
                if not source_id:
                    logger.warning("Received a message with no source_id, skipping.")
                    return
                logger.info(f"Kafka job for source_id: {source_id}")
                try:
                    mind_map = await self.pipeline.generate_from_source_id(source_id)
                    await self._send_result(producer, source_id, mind_map, "success")
                    logger.info(f"Completed result for source_id: {source_id}")
                except Exception as e:
                    logger.error(f"Failed on source_id {source_id}: {e}")
                    await self._send_result(producer, source_id, {"error": str(e)}, "error")

        logger.info(f"Kafka Consumer listening on topic '{self.input_topic}' with max concurrency {max_concurrent}...")

        bg_tasks = set()
        try:
            async for message in consumer:
                task = asyncio.create_task(process_message(message))
                bg_tasks.add(task)
                task.add_done_callback(bg_tasks.discard)
        except asyncio.CancelledError:
            logger.info("Consumer loop cancelled.")
        except Exception as e:
            logger.error(f"Kafka Consumer Error: {e}")
        finally:
            logger.info("Cleaning up Kafka connections...")
            if bg_tasks:
                await asyncio.gather(*bg_tasks, return_exceptions=True)
            await consumer.stop()
            await producer.stop()
