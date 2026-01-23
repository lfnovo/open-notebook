"""
SmolDocling Integration for Open Notebook

This module provides PDF to Markdown conversion using SmolDocling,
a vision-language model for document understanding.

SmolDocling uses a VLM (Vision-Language Model) to process PDF pages as images
and extract structured content including:
- Text with proper formatting
- Tables
- Mathematical formulas
- Code blocks
- Charts and figures

The output is exported to Markdown format for use in the notebook.

This implementation uses the direct transformers approach for more control
over the model and generation parameters.
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass

from loguru import logger


@dataclass
class SmolDoclingResult:
    """Result from SmolDocling document conversion"""
    content: str  # Markdown content
    title: Optional[str] = None
    page_count: int = 0
    success: bool = True
    error_message: Optional[str] = None
    doctags: Optional[str] = None  # Raw DocTags for debugging


class SmolDoclingParser:
    """
    Parser that uses SmolDocling model directly via transformers to convert PDFs to Markdown.
    
    SmolDocling is a 256M parameter vision-language model specifically designed
    for document understanding. It can:
    - Extract text with OCR
    - Recognize tables and convert to markdown
    - Parse mathematical formulas to LaTeX
    - Identify code blocks
    - Process charts and figures
    
    This implementation uses the direct transformers approach for:
    - More control over generation parameters
    - bfloat16 for memory efficiency
    - Access to raw DocTags output
    """
    
    MODEL_NAME = "ds4sd/SmolDocling-256M-preview"
    
    def __init__(self, use_gpu: bool = True, max_new_tokens: int = 8192):
        """
        Initialize the SmolDocling parser.
        
        Args:
            use_gpu: Whether to use GPU acceleration if available
            max_new_tokens: Maximum tokens to generate per page (default 8192)
        """
        self.use_gpu = use_gpu
        self.max_new_tokens = max_new_tokens
        self._processor = None
        self._model = None
        self._device = None
        self._initialized = False
        
        # Chat template for the model
        self._messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": "Convert this page to docling."}
                ]
            },
        ]
    
    def _initialize(self):
        """Lazy initialization of the model and processor"""
        if self._initialized:
            return
            
        try:
            import torch
            from transformers import AutoProcessor, AutoModelForVision2Seq
            
            # Determine device
            if torch.cuda.is_available() and self.use_gpu:
                self._device = "cuda"
                logger.info("SmolDocling: Using CUDA GPU acceleration")
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available() and self.use_gpu:
                self._device = "mps"
                logger.info("SmolDocling: Using MPS (Apple Silicon) acceleration")
            else:
                self._device = "cpu"
                logger.info("SmolDocling: Using CPU (no GPU acceleration)")
            
            logger.info(f"SmolDocling: Loading model {self.MODEL_NAME}...")
            
            # Load processor
            self._processor = AutoProcessor.from_pretrained(self.MODEL_NAME)
            
            # Load model with bfloat16 for memory efficiency
            self._model = AutoModelForVision2Seq.from_pretrained(
                self.MODEL_NAME,
                torch_dtype=torch.bfloat16,
                _attn_implementation="eager"
            ).to(self._device)
            
            self._initialized = True
            logger.info(f"SmolDocling: Model loaded successfully on {self._device}")
            
        except ImportError as e:
            logger.error(f"Failed to import required libraries: {e}")
            logger.error("Please install: pip install transformers torch docling-core pillow pdf2image")
            raise ImportError(
                "SmolDocling requires additional dependencies. "
                "Install with: pip install transformers torch docling-core pillow pdf2image"
            ) from e
    
    def _process_image(self, image) -> Tuple[str, str]:
        """
        Process a single image through the model.
        
        Args:
            image: PIL Image object
            
        Returns:
            Tuple of (doctags_string, markdown_string)
        """
        import torch
        from docling_core.types.doc import DocTagsDocument, DoclingDocument
        
        # Prepare prompt
        prompt = self._processor.apply_chat_template(
            self._messages, 
            add_generation_prompt=True
        )
        
        # Process inputs
        inputs = self._processor(
            text=prompt, 
            images=[image], 
            return_tensors="pt"
        )
        inputs = inputs.to(self._device)
        
        # Generate output
        with torch.no_grad():
            generated_ids = self._model.generate(
                **inputs, 
                max_new_tokens=self.max_new_tokens
            )
        
        # Trim prompt from output
        prompt_length = inputs.input_ids.shape[1]
        trimmed_generated_ids = generated_ids[:, prompt_length:]
        
        # Decode to DocTags
        doctags = self._processor.batch_decode(
            trimmed_generated_ids,
            skip_special_tokens=False,
        )[0].lstrip()
        
        # Convert DocTags to DoclingDocument
        doctags_doc = DocTagsDocument.from_doctags_and_image_pairs([doctags], [image])
        doc = DoclingDocument.load_from_doctags(doctags_doc, document_name="Document")
        
        # Export to markdown
        markdown = doc.export_to_markdown()
        
        return doctags, markdown
    
    def _pdf_to_images(self, file_path: str) -> List:
        """Convert PDF pages to PIL Images"""
        from pdf2image import convert_from_path
        
        images = convert_from_path(file_path)
        logger.info(f"SmolDocling: Converted PDF to {len(images)} page images")
        return images
    
    def _load_image(self, file_path: str):
        """Load a single image file"""
        from PIL import Image
        return Image.open(file_path).convert("RGB")
    
    async def parse_file(self, file_path: str) -> SmolDoclingResult:
        """
        Parse a PDF or image file using SmolDocling.
        
        Args:
            file_path: Path to the PDF or image file
            
        Returns:
            SmolDoclingResult with markdown content
        """
        try:
            # Initialize if needed
            self._initialize()
            
            path = Path(file_path)
            if not path.exists():
                return SmolDoclingResult(
                    content="",
                    success=False,
                    error_message=f"File not found: {file_path}"
                )
            
            suffix = path.suffix.lower()
            
            # Check supported formats
            if suffix not in ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp']:
                return SmolDoclingResult(
                    content="",
                    success=False,
                    error_message=f"Unsupported file format: {suffix}. SmolDocling supports PDF and image files."
                )
            
            logger.info(f"SmolDocling: Processing file {file_path}")
            
            # Run conversion in thread pool to not block async
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._convert_sync,
                str(path),
                suffix
            )
            
            return result
            
        except Exception as e:
            logger.error(f"SmolDocling parsing failed: {e}")
            logger.exception(e)
            return SmolDoclingResult(
                content="",
                success=False,
                error_message=str(e)
            )
    
    def _convert_sync(self, file_path: str, suffix: str) -> SmolDoclingResult:
        """Synchronous conversion method"""
        try:
            all_markdown = []
            all_doctags = []
            page_count = 0
            
            if suffix == '.pdf':
                # Convert PDF to images and process each page
                images = self._pdf_to_images(file_path)
                page_count = len(images)
                
                for i, image in enumerate(images):
                    logger.info(f"SmolDocling: Processing page {i + 1}/{page_count}")
                    doctags, markdown = self._process_image(image)
                    all_doctags.append(doctags)
                    all_markdown.append(markdown)
            else:
                # Single image
                image = self._load_image(file_path)
                doctags, markdown = self._process_image(image)
                all_doctags.append(doctags)
                all_markdown.append(markdown)
                page_count = 1
            
            # Combine all pages with page separators
            combined_markdown = "\n\n---\n\n".join(all_markdown)
            combined_doctags = "\n\n".join(all_doctags)
            
            logger.info(f"SmolDocling: Successfully converted {file_path} ({page_count} pages)")
            
            return SmolDoclingResult(
                content=combined_markdown,
                title=Path(file_path).stem,
                page_count=page_count,
                success=True,
                doctags=combined_doctags
            )
            
        except Exception as e:
            logger.error(f"SmolDocling conversion error: {e}")
            return SmolDoclingResult(
                content="",
                success=False,
                error_message=str(e)
            )
    
    async def parse_url(self, url: str) -> SmolDoclingResult:
        """
        Parse a PDF from URL using SmolDocling.
        
        Args:
            url: URL to the PDF file
            
        Returns:
            SmolDoclingResult with markdown content
        """
        import aiohttp
        
        try:
            # Download the file first
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return SmolDoclingResult(
                            content="",
                            success=False,
                            error_message=f"Failed to download: HTTP {response.status}"
                        )
                    
                    content = await response.read()
            
            # Determine file extension from URL or content-type
            content_type = response.headers.get('content-type', '')
            if 'pdf' in content_type.lower() or url.lower().endswith('.pdf'):
                suffix = '.pdf'
            elif 'png' in content_type.lower():
                suffix = '.png'
            elif 'jpeg' in content_type.lower() or 'jpg' in content_type.lower():
                suffix = '.jpg'
            else:
                suffix = '.pdf'  # Default to PDF
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                f.write(content)
                temp_path = f.name
            
            try:
                result = await self.parse_file(temp_path)
                return result
            finally:
                # Clean up temp file
                Path(temp_path).unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"SmolDocling URL parsing failed: {e}")
            return SmolDoclingResult(
                content="",
                success=False,
                error_message=str(e)
            )


# Singleton instance for reuse
_parser_instance: Optional[SmolDoclingParser] = None


def get_smol_docling_parser(use_gpu: bool = True, max_new_tokens: int = 8192) -> SmolDoclingParser:
    """
    Get or create a SmolDocling parser instance.
    
    Args:
        use_gpu: Whether to use GPU acceleration
        max_new_tokens: Maximum tokens to generate per page
        
    Returns:
        SmolDoclingParser instance
    """
    global _parser_instance
    
    if _parser_instance is None:
        _parser_instance = SmolDoclingParser(use_gpu=use_gpu, max_new_tokens=max_new_tokens)
    
    return _parser_instance


async def convert_pdf_to_markdown(file_path: str, use_gpu: bool = True) -> SmolDoclingResult:
    """
    Convenience function to convert a PDF to Markdown using SmolDocling.
    
    Args:
        file_path: Path to the PDF file
        use_gpu: Whether to use GPU acceleration
        
    Returns:
        SmolDoclingResult with markdown content
    """
    parser = get_smol_docling_parser(use_gpu=use_gpu)
    return await parser.parse_file(file_path)


def check_smoldocling_available() -> bool:
    """
    Check if SmolDocling dependencies are available.
    
    Returns:
        True if all required packages are installed
    """
    try:
        import transformers
        import torch
        from docling_core.types.doc import DocTagsDocument, DoclingDocument
        from PIL import Image
        import pdf2image
        return True
    except ImportError:
        return False


# For backwards compatibility with Pranay's placeholder
def get_placeholder():
    """
    Legacy placeholder function.
    Now returns availability status of SmolDocling.
    """
    return check_smoldocling_available()
