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

print("DEBUG: Importing required libraries completed.")

# Ensure NLTK models are available
print("DEBUG: Downloading NLTK models...")
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('averaged_perceptron_tagger_eng', quiet=True) 
nltk.download('maxent_ne_chunker', quiet=True)
nltk.download('maxent_ne_chunker_tab', quiet=True) 
nltk.download('words', quiet=True)
print("DEBUG: NLTK models download completed.")

# -------------------------------------------------
# LOGGER
# -------------------------------------------------
print("DEBUG: Setting up logger...")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MindMapPipeline")
print("DEBUG: Logger setup completed.")

# ============================================================================
# 1. OCR LAYER (Multithreaded EasyOCR Extraction)
# ============================================================================
class EasyOCRService:
    def __init__(self, langs: List[str] = ['en'], max_threads: int = 4):
        print(f"DEBUG: Initializing EasyOCRService with langs={langs}, max_threads={max_threads}")
        logger.info("Loading EasyOCR models...")
        # PRO TIP: If you have a GPU, setting gpu=True here will speed up OCR by ~10x
        print("DEBUG: Creating easyocr.Reader instance...")
        self.reader = easyocr.Reader(langs, gpu=False)
        self.max_threads = max_threads
        print("DEBUG: EasyOCRService initialization completed.")

    def _extract_sync(self, file_path: str) -> str:
        print(f"DEBUG: _extract_sync called with file_path={file_path}")
        logger.info(f"📖 Extracting text from: {file_path}")
        
        if file_path.lower().endswith('.pdf'):
            print("DEBUG: Detected PDF file format.")
            text_results = []
            print("DEBUG: Opening PDF document...")
            with fitz.open(file_path) as doc:
                print(f"DEBUG: PDF opened. Total pages: {len(doc)}")
                for i, page in enumerate(doc):
                    print(f"DEBUG: Extracting text from page {i+1}...")
                    text_results.append(page.get_text())
            
            print("DEBUG: Joining extracted text...")
            combined_text = "\n".join(text_results).strip()
            print(f"DEBUG: Combined text length: {len(combined_text)}")
            
            if len(combined_text) < 50:
                print("DEBUG: Extracted text is less than 50 characters. Assuming scanned PDF.")
                logger.info("📄 PDF looks like a scanned image. Using MULTITHREADED OCR...")
                print("DEBUG: Converting PDF pages to images...")
                images = convert_from_path(file_path)
                print(f"DEBUG: Converted {len(images)} images.")
                
                def process_image(img):
                    print("DEBUG: process_image called.")
                    # OPTIMIZED: Added batch_size to process faster if GPU/RAM allows
                    return self.reader.readtext(np.array(img), detail=0, batch_size=4)

                ocr_results = []
                workers = min(self.max_threads, len(images)) if images else 1
                print(f"DEBUG: Starting ThreadPoolExecutor with {workers} workers...")
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                    print("DEBUG: Mapping images to executor...")
                    results = list(executor.map(process_image, images))
                    print("DEBUG: Aggregating OCR results...")
                    for res in results:
                        ocr_results.extend(res)
                        
                print("DEBUG: Returning joined OCR results.")
                return "\n".join(ocr_results)
            
            print("DEBUG: Returning combined text from PDF.")
            return combined_text
        else:
            print("DEBUG: Detected non-PDF file. Using EasyOCR directly...")
            result = "\n".join(self.reader.readtext(file_path, detail=0))
            print("DEBUG: EasyOCR extraction completed.")
            return result

    async def extract_text_async(self, file_path: str) -> str:
        print(f"DEBUG: extract_text_async called with file_path={file_path}")
        result = await asyncio.to_thread(self._extract_sync, file_path)
        print("DEBUG: extract_text_async completed.")
        return result


# ============================================================================
# 2. TEXT PROCESSING LAYER (Optimized NLP)
# ============================================================================
class TextProcessor:
    def __init__(self, nlp_model_name: str = "en_core_web_sm"):
        print(f"DEBUG: Initializing TextProcessor with model={nlp_model_name}")
        try:
            print("DEBUG: Importing pytextrank...")
            import pytextrank  # noqa: F401 — lazy import avoids gitpython at module load
            # parser is required by pytextrank — do NOT disable it
            print("DEBUG: Loading spaCy model...")
            self.nlp = spacy.load(nlp_model_name, disable=["textcat"])
            print("DEBUG: Adding textrank pipe to spaCy model...")
            self.nlp.add_pipe("textrank")
        except OSError:
            print(f"DEBUG: OSError caught. Model '{nlp_model_name}' not found.")
            logger.error(f"spaCy model '{nlp_model_name}' not found. Run: python -m spacy download {nlp_model_name}")
            raise

        print("DEBUG: Compiling clean_patterns...")
        self.clean_patterns = [
            (re.compile(r' |&NBSP;', re.I), ' '),
            (re.compile(r'=+\s*PAGE\s*\d+\s*=+', re.I), ' '),
            (re.compile(r'\b\d+\.\b'), ' '),
            (re.compile(r'(\w)\n(\w)'), r'\1 \2'),
            (re.compile(r'\n+'), '\n'),
            (re.compile(r'\s+'), ' '),
        ]

        # Words that often get falsely tagged as people in police documents
        print("DEBUG: Initializing bad_name_keywords...")
        self.bad_name_keywords = {"police", "officer", "court", "station", "security", "type", "status", "alias", "dossier", "unknown", "fir", "act"}
        print("DEBUG: TextProcessor initialization completed.")

    def _sync_clean(self, text: str) -> str:
        print("DEBUG: _sync_clean called.")
        if not text: 
            print("DEBUG: Empty text provided to _sync_clean.")
            return ""
        for pattern, replacement in self.clean_patterns:
            print(f"DEBUG: Applying pattern {pattern}...")
            text = pattern.sub(replacement, text)
        print("DEBUG: Returning cleaned text.")
        return text.strip()

    async def clean_ocr_text(self, text: str) -> str:
        print("DEBUG: clean_ocr_text called.")
        result = await asyncio.to_thread(self._sync_clean, text)
        print("DEBUG: clean_ocr_text completed.")
        return result
    
    def _sync_detect_person(self, text: str) -> str:
        print("DEBUG: _sync_detect_person called.")
        logger.info("🧠 NLP is performing Named Entity Extraction...")
        
        # 1. Pre-process text to help spaCy. 
        # OCR often returns ALL CAPS. Title casing helps the NER model identify proper nouns correctly.
        print("DEBUG: Title casing text...")
        processed_text = text.title()
        
        print(f"DEBUG: Setting spaCy max_length. Original max_length: {self.nlp.max_length}")
        self.nlp.max_length = max(len(processed_text) + 100, 1000000)
        print(f"DEBUG: Running spaCy pipeline on processed_text (length: {len(processed_text)})...")
        doc = self.nlp(processed_text)
        
        candidates = []
        
        # 2. Extract standard PERSON entities using spaCy's trained model
        print("DEBUG: Extracting PERSON entities...")
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                clean_name = ent.text.strip()
                print(f"DEBUG: Found PERSON entity: {clean_name}")
                # Filter out obvious noise: too short, too long, or containing bad keywords
                if 2 < len(clean_name) < 25 and not any(bad in clean_name.lower() for bad in self.bad_name_keywords):
                    print(f"DEBUG: Adding candidate: {clean_name}")
                    candidates.append(clean_name)
                else:
                    print(f"DEBUG: Rejecting entity: {clean_name}")

        # 3. Fallback/Supplement: Regex for explicit "Name: X" patterns
        # Look for "Name" followed by optional punctuation, then grab 1-3 capitalized words.
        print("DEBUG: Applying fallback regex for names...")
        name_matches = re.findall(r'\bName\b[\s\:\-]+([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,2})', processed_text)
        for match in name_matches:
            print(f"DEBUG: Regex found match: {match}")
            if len(match) > 2 and not any(bad in match.lower() for bad in self.bad_name_keywords):
                print(f"DEBUG: Adding regex candidate: {match.strip()}")
                candidates.append(match.strip())

        # 4. Score and select the best candidate
        if not candidates:
            print("DEBUG: No candidates found.")
            logger.warning("⚠️ NLP could not confidently find a person's name. Defaulting to 'Target Subject'.")
            return "Target Subject"

        # Count frequencies of extracted names
        print("DEBUG: Counting candidate frequencies...")
        name_counts = Counter(candidates)
        
        best_name = "Target Subject"
        best_score = -999
        
        print("DEBUG: Scoring candidates...")
        for name, count in name_counts.items():
            word_count = len(name.split())
            score = count
            print(f"DEBUG: Initial score for {name}: {score}")
            
            # Bonus for full names (First Last)
            if word_count == 2:
                score += 3
                print(f"DEBUG: Added +3 bonus for full name. New score: {score}")
            # Bonus for First Middle Last
            elif word_count == 3:
                score += 1
                print(f"DEBUG: Added +1 bonus for middle name. New score: {score}")
            
            # Heavy penalty for single letters or massive run-on phrases
            if word_count > 4 or len(name) < 3:
                score -= 10
                print(f"DEBUG: Applied -10 penalty. New score: {score}")
                
            if score > best_score:
                print(f"DEBUG: New best score found: {name} ({score})")
                best_score = score
                best_name = name

        # Final safety check in case the best score is still terrible
        print(f"DEBUG: Final score check. best_score: {best_score}")
        if best_score < -5:
            print("DEBUG: Best score is less than -5. Picking most common candidate.")
            winner = name_counts.most_common(1)[0][0] # Just grab the most frequent one
        else:
            print("DEBUG: Using best scored candidate.")
            winner = best_name
            
        logger.info(f"🎯 NLP Extracted Name: {winner}")
        return winner

    async def detect_main_person_async(self, text: str) -> Optional[str]:
        print("DEBUG: detect_main_person_async called.")
        result = await asyncio.to_thread(self._sync_detect_person, text)
        print("DEBUG: detect_main_person_async completed.")
        return result

    @staticmethod
    def deduplicate_facts(facts: List[str]) -> List[str]:
        print("DEBUG: deduplicate_facts called.")
        seen = set()
        clean = []
        for f in facts:
            print(f"DEBUG: Processing fact: {f[:50]}...")
            key = re.sub(r"\W+", "", f.lower())
            if key not in seen:
                print(f"DEBUG: Adding unique fact. Key: {key}")
                seen.add(key)
                clean.append(f.strip())
            else:
                print(f"DEBUG: Skipping duplicate fact. Key: {key}")
        print(f"DEBUG: deduplicate_facts completed. Original: {len(facts)}, Cleaned: {len(clean)}")
        return clean
        
# ============================================================================
# 3. LLM SERVICE LAYER (Prompts & Invocation)
# ============================================================================
class IntelligenceLLMService:
    """Manages LangChain prompts and LLM interactions asynchronously."""
    
    def __init__(self, llm):
        print("DEBUG: Initializing IntelligenceLLMService...")
        self.llm = llm

        print("DEBUG: Defining fact_system_prompt...")
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
        print("DEBUG: Creating fact_chain...")
        self.fact_chain = ChatPromptTemplate.from_messages([
            ("system", self.fact_system_prompt),
            ("human", "Document Text to Analyze:\n\n{context}")
        ]) | self.llm | StrOutputParser()
        
        logger.info("Mind Map Chain Initialized...")
        print("DEBUG: Creating mindmap_chain...")
        # UPDATED: Prompt tailored perfectly to match the reference Mind Map image structure
        self.mindmap_chain = ChatPromptTemplate.from_messages([
    ("system", """You are an expert information architect creating a logically structured JSON mind map from the provided document data.

HIERARCHY RULES:
1. Root (Level 0): Use a concise, highly descriptive title representing the main subject of the document (e.g., '{subject} Overview' or the document's main title) as the Root label.
2. Categories (Level 1): Dynamically extract the most logical main themes, sections, or categories based entirely on the provided context. Do NOT use pre-determined categories.
3. Sub-Categories (Level 2+): Where appropriate, create sub-categories to logically group related information within a main category. 
4. Facts (Leaf Nodes): Represent the actual data points, facts, or details as concise strings. If the data naturally forms pairs, use a 'Key: Value' format (e.g., 'Release Date: 2024', 'Status: Active'). Otherwise, use short, clear statements.

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
        print("DEBUG: IntelligenceLLMService initialization completed.")

    def extract_facts_sync(self, text_chunk: str) -> List[str]:
        print("DEBUG: extract_facts_sync called.")
        """Synchronous version to support the concurrent ThreadPoolExecutor pipeline."""
        try:
            print("DEBUG: Invoking fact_chain...")
            raw_response = self.fact_chain.invoke({"context": text_chunk})
            print("DEBUG: fact_chain invocation completed. Cleaning response...")
            raw_facts = raw_response.strip().removeprefix("```json").removesuffix("```").strip()
            print("DEBUG: Parsing JSON response...")
            parsed = json.loads(raw_facts)
            extracted = []
            
            if isinstance(parsed, list):
                print("DEBUG: Parsed response is a list. Extracting items...")
                for item in parsed:
                    if isinstance(item, str):   
                        extracted.append(item)
                    elif isinstance(item, dict) and "fact" in item:
                        extracted.append(str(item["fact"]))
                        
            print(f"DEBUG: Returning {len(extracted)} extracted facts.")
            return extracted
        except Exception as e:
            print(f"DEBUG: Exception caught in extract_facts_sync: {e}")
            logger.warning(f"Fact extraction parsing failed, skipping chunk. Error: {e}")
            return []

    async def extract_facts_async(self, text_chunk: str, images_b64: Optional[List[str]] = None) -> List[str]:
        print("DEBUG: extract_facts_async called.")
        try:
            print("DEBUG: Formatting human_message...")
            message_content = [{"type": "text", "text": f"Document Text to Analyze:\n\n{text_chunk[:10000]}"}]
            
            if images_b64:
                print(f"DEBUG: Adding {len(images_b64)} images to message_content...")
                for img_data in images_b64:
                    message_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}
                    })
            
            human_message = HumanMessage(content=message_content)

            print("DEBUG: Calling llm.ainvoke...")
            # Native Async Invoke (Massive speed up for parallel requests)
            raw_response = await self.llm.ainvoke([
                {"role": "system", "content": self.fact_system_prompt}, 
                human_message
            ])
            
            print("DEBUG: llm.ainvoke completed. Parsing response...")
            parser = StrOutputParser()
            raw_facts = parser.invoke(raw_response)
            
            print("DEBUG: Cleaning raw JSON string...")
            raw_facts = raw_facts.strip().removeprefix("```json").removesuffix("```").strip()
            print("DEBUG: Loading JSON string...")
            parsed = json.loads(raw_facts)
            extracted = []
            
            if isinstance(parsed, list):
                print("DEBUG: Processing parsed list...")
                for item in parsed:
                    if isinstance(item, str):   
                        extracted.append(item)
                    elif isinstance(item, dict) and "fact" in item:
                        extracted.append(str(item["fact"]))
                        
            print(f"DEBUG: Returning {len(extracted)} facts.")
            return extracted
            
        except Exception as e:
            print(f"DEBUG: Exception caught in extract_facts_async: {e}")
            logger.warning(f"Fact extraction parsing failed, skipping chunk. Error: {e}")
            return []

    async def generate_mind_map_async(self, person: str, facts: List[str]) -> Dict:
        print(f"DEBUG: generate_mind_map_async called for person: {person}")
        print("DEBUG: Invoking mindmap_chain.ainvoke...")
        result = await self.mindmap_chain.ainvoke({
            "subject": person,
            "context": json.dumps(facts, indent=2)
        })
        print("DEBUG: mindmap_chain.ainvoke completed.")
        return result


# ============================================================================
# 4. ORCHESTRATOR LAYER (Local Processing)
# ============================================================================
class MindMapPipeline:
    """Coordinates Local Data Fetching -> NLP Processing -> LLM Execution."""
    
    def __init__(self, ocr_service: EasyOCRService, processor: TextProcessor, llm_service: IntelligenceLLMService):
        print("DEBUG: Initializing MindMapPipeline...")
        self.ocr_service = ocr_service
        self.processor = processor
        self.llm_service = llm_service
        print("DEBUG: MindMapPipeline initialization completed.")

    async def generate_from_source_id(self, source_id: str) -> Dict:
        print(f"DEBUG: generate_from_source_id called with source_id: {source_id}")
        """Fetches the source by ID, extracts/gets text, and generates the mind map."""
        # Local import to prevent circular dependencies in FastAPI apps
        print("DEBUG: Importing Source from open_notebook.domain.notebook...")
        from open_notebook.domain.notebook import Source
        
        logger.info(f"🚀 Starting Mind Map Generation for Source ID: {source_id}")
        
        # 1. Fetch Source
        print("DEBUG: Fetching Source from database...")
        source = await Source.get(source_id)
        if not source:
            print("DEBUG: Source not found.")
            logger.error(f"❌ Source not found for id: {source_id}")
            return {"label": "Target Subject", "children": [{"label": "Source not found."}]}

        print("DEBUG: Source fetched successfully.")
        # 2. Get Text (either from DB or via OCR fallback)
        full_text = ""
        if source.full_text and source.full_text.strip():
            print("DEBUG: source.full_text is present.")
            logger.info("📄 Using extracted text from database.")
            full_text = source.full_text
        elif source.asset and source.asset.file_path:
            print("DEBUG: source.full_text missing. Calling OCR fallback on asset file_path...")
            logger.info("🖼️ No text in DB, performing OCR on file...")
            full_text = await self.ocr_service.extract_text_async(source.asset.file_path)

        if not full_text:
            print("DEBUG: full_text is empty after fetching/OCR.")
            return {"label": "Target Subject", "children": [{"label": "No data/text found to process."}]}

        print("DEBUG: Starting text processing...")
        # 3. Clean and Process Text
        clean_text = await self.processor.clean_ocr_text(full_text)
        print("DEBUG: Text cleaning completed. Detecting main person...")
        main_person = await self.processor.detect_main_person_async(clean_text) or "Target Subject"
        print(f"DEBUG: Main person detected: {main_person}")
        
        # 4. Extract Facts in Concurrent Chunks (Optimized with asyncio)
        print("DEBUG: Chunking clean_text...")
        text_chunks = [clean_text[i:i+10000] for i in range(0, len(clean_text), 10000)]
        all_facts = []
        
        logger.info(f"🧠 Extracting facts across {len(text_chunks)} chunks concurrently...")
        print("DEBUG: Creating asyncio tasks for extract_facts_sync...")
        tasks = [asyncio.to_thread(self.llm_service.extract_facts_sync, chunk) for chunk in text_chunks]
        print("DEBUG: Gathering asyncio tasks...")
        chunk_results = await asyncio.gather(*tasks)
        print("DEBUG: Chunk results gathered.")
            
        for i, result in enumerate(chunk_results):
            print(f"DEBUG: Processing chunk {i} result...")
            if isinstance(result, list): 
                all_facts.extend(result)

        print("DEBUG: Deduplicating facts...")
        facts = self.processor.deduplicate_facts(all_facts)
        if not facts:
            print("DEBUG: No extractable facts found after deduplication.")
            return {"label": f"{main_person} Dossier", "children": [{"label": "No extractable facts found."}]}

        print("DEBUG: Generating mind map JSON...")
        # 5. Build JSON Mind Map
        result = await self.llm_service.generate_mind_map_async(main_person, facts)
        print("DEBUG: generate_from_source_id completed.")
        return result


    def _fallback_mind_map(self, person: str, facts: List[str]) -> Dict:
        print("DEBUG: _fallback_mind_map called.")
        buckets = defaultdict(list)
        for fact in facts:
            print(f"DEBUG: Bucketing fact: {fact[:50]}...")
            f = fact.lower()
            if any(k in f for k in ["resident", "born", "age"]):
                buckets["Identity & Background"].append(fact)
            elif any(k in f for k in ["fir", "arrest", "crime", "case"]):
                buckets["Criminal History"].append(fact)
            else:
                buckets["Other Details"].append(fact)

        print("DEBUG: Generating fallback dictionary structure...")
        result = {
            "label": person,
            "children": [{"label": k, "children": [{"label": f} for f in v]} for k, v in buckets.items() if v]
        }
        print("DEBUG: _fallback_mind_map completed.")
        return result


# ============================================================================
# 5. KAFKA ORCHESTRATOR LAYER (Distributed Processing)
# ============================================================================
class KafkaMindMapOrchestrator:
    """
    Wraps the MindMapPipeline with Kafka Producer and Consumer logic.
    Allows for distributed processing across multiple machines or containers.
    """
    
    def __init__(
        self, 
        pipeline: Optional[MindMapPipeline], 
        bootstrap_servers: str = None,
        input_topic: str = 'mindmap_jobs',
        output_topic: str = 'mindmap_results',
        group_id: str = 'mindmap_worker_group'
    ):
        print("DEBUG: Initializing KafkaMindMapOrchestrator...")
        import os
        self.pipeline = pipeline
        self.bootstrap_servers = bootstrap_servers or os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9093")
        self.input_topic = input_topic
        self.output_topic = output_topic
        self.group_id = group_id
        print("DEBUG: KafkaMindMapOrchestrator initialization completed.")

    async def produce_jobs(self, source_ids: List[str]):
        print(f"DEBUG: produce_jobs called with source_ids: {source_ids}")
        """Produces source processing jobs to the Kafka input topic."""
        print("DEBUG: Creating AIOKafkaProducer...")
        producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers)
        print("DEBUG: Starting AIOKafkaProducer...")
        await producer.start()
        
        logger.info(f"📤 Starting Kafka Producer. Sending {len(source_ids)} jobs...")
        try:
            for sid in source_ids:
                print(f"DEBUG: Preparing payload for source_id: {sid}")
                payload = {"source_id": sid}
                message_bytes = json.dumps(payload).encode('utf-8')
                print(f"DEBUG: Sending message to topic: {self.input_topic}...")
                await producer.send_and_wait(self.input_topic, message_bytes)
                logger.info(f"✅ Published job for source_id: {sid}")
        except Exception as e:
            print(f"DEBUG: Exception caught in produce_jobs: {e}")
            logger.error(f"❌ Failed to produce Kafka messages: {e}")
        finally:
            print("DEBUG: Stopping producer...")
            await producer.stop()
            logger.info("🛑 Kafka Producer stopped.")

    async def _send_result(self, producer: AIOKafkaProducer, source_id: str, result: Dict[str, Any], status: str):
        print(f"DEBUG: _send_result called for source_id: {source_id}, status: {status}")
        """Helper to send the final mind map back to an output topic."""
        payload = {
            "source_id": source_id,
            "status": status,
            "data": result
        }
        print("DEBUG: Encoding payload...")
        message_bytes = json.dumps(payload).encode('utf-8')
        print(f"DEBUG: Sending result to topic: {self.output_topic}...")
        await producer.send_and_wait(self.output_topic, message_bytes)
        print("DEBUG: _send_result completed.")

    async def start_consumer(self, max_concurrent: int = 3):
        print(f"DEBUG: start_consumer called with max_concurrent: {max_concurrent}")
        """
        Consumes jobs from Kafka and processes them concurrently up to a strict limit.
        Uses asyncio.Semaphore instead of local queues to prevent overwhelming local hardware.
        """
        print("DEBUG: Creating AIOKafkaConsumer...")
        consumer = AIOKafkaConsumer(
            self.input_topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset='earliest'
        )
        
        print("DEBUG: Creating AIOKafkaProducer for results...")
        producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers)
        
        print("DEBUG: Starting consumer...")
        await consumer.start()
        print("DEBUG: Starting producer...")
        await producer.start()

        print(f"DEBUG: Creating asyncio.Semaphore with value {max_concurrent}...")
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_message(msg):
            print("DEBUG: process_message called.")
            async with semaphore:
                print("DEBUG: Semaphore acquired.")
                payload = json.loads(msg.value.decode('utf-8'))
                source_id = payload.get("source_id")
                
                if not source_id:
                    print("DEBUG: source_id missing in payload.")
                    logger.warning("Received a message with no source_id, skipping.")
                    return
                
                logger.info(f"👷 Picked up Kafka job directly for source_id: {source_id}")
                try:
                    print(f"DEBUG: Calling pipeline.generate_from_source_id for {source_id}...")
                    mind_map = await self.pipeline.generate_from_source_id(source_id)
                    print("DEBUG: Mind map generated. Sending result...")
                    await self._send_result(producer, source_id, mind_map, "success")
                    logger.info(f"🎉 Completed and published result for source_id: {source_id}")
                except Exception as e:
                    print(f"DEBUG: Exception caught in process_message for {source_id}: {e}")
                    logger.error(f"❌ Failed on source_id {source_id}: {e}")
                    await self._send_result(producer, source_id, {"error": str(e)}, "error")
            print("DEBUG: Semaphore released.")

        logger.info(f"🎧 Kafka Consumer listening on topic '{self.input_topic}' with max concurrency {max_concurrent}...")
        
        bg_tasks = set()
        
        try:
            print("DEBUG: Entering async for loop over consumer...")
            async for message in consumer:
                print("DEBUG: Message received from consumer.")
                task = asyncio.create_task(process_message(message))
                bg_tasks.add(task)
                task.add_done_callback(bg_tasks.discard)
                
        except asyncio.CancelledError:
            print("DEBUG: CancelledError caught in consumer loop.")
            logger.info("Consumer loop cancelled.")
        except Exception as e:
            print(f"DEBUG: Exception caught in consumer loop: {e}")
            logger.error(f"Kafka Consumer Error: {e}")
        finally:
            print("DEBUG: Finally block executing in start_consumer...")
            logger.info("Cleaning up Kafka connections...")
            if bg_tasks:
                print(f"DEBUG: Awaiting {len(bg_tasks)} background tasks...")
                await asyncio.gather(*bg_tasks, return_exceptions=True)
            print("DEBUG: Stopping consumer...")
            await consumer.stop()
            print("DEBUG: Stopping producer...")
            await producer.stop()
            print("DEBUG: start_consumer completed.")