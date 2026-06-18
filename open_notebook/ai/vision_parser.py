import base64
import os
from typing import List, Optional

from esperanto import LanguageModel
from langchain_core.messages import HumanMessage
from loguru import logger

from open_notebook.ai.models import model_manager

VISION_PROMPT = """
Analyze this image in detail.
1. Extract all visible text accurately (OCR).
2. Describe any charts, graphs, diagrams, or visual structures in deep detail.
3. CRITICAL: If there are charts, plots, or diagrams, you MUST list all specific labels, data points, categories, variable names, gene names, or exact values shown. Do not just summarize trends; provide the exact names and labels visible in the figure.
4. Provide a rich contextual description of what is happening in the image.

Output the result in a clear, structured Markdown format.
"""

def _encode_image_to_base64(file_path: str) -> str:
    """Encode an image file to base64 string."""
    with open(file_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def _get_mime_type(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext in [".jpg", ".jpeg"]:
        return "image/jpeg"
    elif ext == ".png":
        return "image/png"
    elif ext == ".webp":
        return "image/webp"
    return "image/jpeg"

async def _analyze_base64_image(b64_image: str, mime_type: str, vision_model: LanguageModel) -> str:
    """Send base64 image to the vision model and return the parsed text."""
    # Bypass esperanto's schema casting which may stringify multimodal arrays
    raw_llm = vision_model.to_langchain()
    
    # Bypass buggy langchain_community wrapper for Ollama vision models
    if raw_llm.__class__.__name__ == "ChatOllama":
        import httpx
        base_url = getattr(raw_llm, "base_url", "http://localhost:11434")
        if isinstance(base_url, str):
            base_url = base_url.rstrip("/")
        model_name = getattr(raw_llm, "model", "llama3.2-vision")
        
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": VISION_PROMPT,
                    "images": [b64_image]
                }
            ],
            "stream": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=1800.0) as client:
                response = await client.post(f"{base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
                content = data.get("message", {}).get("content", "")
                if not content:
                    logger.warning(f"Ollama returned empty content. Full response: {data}")
                return content
        except Exception as e:
            logger.error(f"Direct Ollama vision parsing failed: {str(e)}")
            raise

    # Fallback for other providers (OpenAI, Anthropic, etc.)
    message = HumanMessage(
        content=[
            {"type": "text", "text": VISION_PROMPT},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{b64_image}"},
            },
        ]
    )
    
    try:
        response = await raw_llm.ainvoke([message])
        content = response.content if hasattr(response, "content") else str(response)
        if isinstance(content, list):
            return "".join([b.get("text", "") if isinstance(b, dict) and b.get("type") == "text" else str(b) for b in content])
        return str(content)
    except Exception as e:
        logger.error(f"Vision parsing failed: {str(e)}")
        raise

async def process_image_with_vision(file_path: str) -> Optional[str]:
    """
    Process a single image file with the default vision model.
    Returns the parsed text, or None if vision is disabled or fails.
    """
    vision_model = await model_manager.get_vision_model()
    if not vision_model:
        return None

    logger.info(f"Using vision parsing for image: {file_path}")
    try:
        mime_type = _get_mime_type(file_path)
        import asyncio
        b64_image = await asyncio.to_thread(_encode_image_to_base64, file_path)
        return await _analyze_base64_image(b64_image, mime_type, vision_model)
    except Exception as e:
        logger.error(f"Failed to process image with vision model: {e}")
        return None

async def process_pdf_with_vision(file_path: str) -> Optional[str]:
    """
    Process a PDF file by extracting images and sending them to the vision model.
    Returns the concatenated parsed text from all pages, or None if disabled/fails.
    """
    vision_model = await model_manager.get_vision_model()
    if not vision_model:
        return None

    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF (fitz) is not installed. Falling back to standard PDF extraction.")
        return None

    logger.info(f"Using vision parsing for PDF: {file_path}")
    
    import asyncio
    
    MAX_PAGES = 50

    def _extract_page_base64(path: str, page_num: int) -> str:
        # Open inside the thread to avoid sharing C-objects across threads
        with fitz.open(path) as doc:
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("jpeg")
            return base64.b64encode(img_bytes).decode("utf-8")
        
    try:
        # Get page count (quick, non-blocking)
        with fitz.open(file_path) as doc:
            total_pages = len(doc)
            
        page_count = min(total_pages, MAX_PAGES)
        if total_pages > MAX_PAGES:
            logger.warning(f"PDF {file_path} has {total_pages} pages. Truncating to {MAX_PAGES} for vision parsing.")
        
        extracted_texts = []

        for page_num in range(page_count):
            logger.info(f"Rendering PDF {file_path} page {page_num + 1}/{page_count}...")
            # Run rendering in a separate thread to prevent blocking the async event loop
            b64_image = await asyncio.to_thread(_extract_page_base64, file_path, page_num)
            
            logger.info(f"Processing PDF {file_path} page {page_num + 1}/{page_count} with vision...")
            page_text = await _analyze_base64_image(b64_image, "image/jpeg", vision_model)
            
            extracted_texts.append(f"## Page {page_num + 1}\n\n{page_text}")

        return "\n\n".join(extracted_texts)

    except Exception as e:
        logger.error(f"Failed to process PDF with vision model: {e}")
        return None
