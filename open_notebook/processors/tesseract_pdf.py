"""
Tesseract OCR processor for scanned PDFs
Integrates with content-core pipeline
"""

from pathlib import Path
from typing import Optional

from pdf2image import convert_from_path
import pytesseract
from loguru import logger


def extract_text_from_scanned_pdf(pdf_path: str, dpi: int = 300) -> str:
    """
    Extract text from scanned PDF using Tesseract OCR.
    
    Args:
        pdf_path: Path to the PDF file
        dpi: Resolution for PDF to image conversion (higher = better quality, slower)
        
    Returns:
        Extracted text from all pages
    """
    try:
        logger.info(f"Converting PDF to images for OCR: {Path(pdf_path).name}")
        
        # Convert PDF pages to images
        images = convert_from_path(pdf_path, dpi=dpi)
        logger.info(f"Converted {len(images)} page(s), running OCR...")
        
        # Extract text from each page
        pages_text = []
        for i, image in enumerate(images, 1):
            logger.debug(f"OCR processing page {i}/{len(images)}")
            text = pytesseract.image_to_string(image, lang='eng')
            if text.strip():
                pages_text.append(text)
        
        full_text = "\n\n".join(pages_text)
        logger.info(f"OCR complete: extracted {len(full_text)} characters from {len(images)} pages")
        
        return full_text
        
    except Exception as e:
        logger.error(f"Tesseract OCR failed for {pdf_path}: {e}")
        raise


def should_use_ocr(pdf_path: str, initial_text: Optional[str] = None) -> bool:
    """
    Determine if OCR should be used for this PDF.
    
    Args:
        pdf_path: Path to PDF file
        initial_text: Text extracted by standard PDF reader (if any)
        
    Returns:
        True if OCR should be used
    """
    # If no text was extracted, definitely use OCR
    if not initial_text or len(initial_text.strip()) < 100:
        logger.info(f"PDF has little/no extractable text, will use OCR")
        return True
    
    # If text is mostly image placeholders, use OCR
    if initial_text.count("<!-- image -->") > 10:
        logger.info(f"PDF contains mostly images, will use OCR")
        return True
    
    # Otherwise, standard extraction is fine
    return False