import asyncio
import re
import unicodedata

import fitz  # type: ignore
from loguru import logger

from open_notebook.graphs.content_processing.state import ContentState

# todo: find tables - https://pymupdf.readthedocs.io/en/latest/the-basics.html#extracting-tables-from-a-page
# todo: what else can we do to make the text more readable?
# todo: try to fix encoding for some PDF that is still breaking
# def _extract_text_from_pdf(pdf_path):
#     doc = fitz.open(pdf_path)
#     text = ""
#     logger.debug(f"Found {len(doc)} pages in PDF")
#     for page in doc:
#         # Use encode/decode if you need to clean up any encoding issues
#         text += page.get_text().encode('utf-8').decode('utf-8')
#     doc.close()
#     return text

SUPPORTED_FITZ_TYPES = [
    "application/pdf",
    "application/epub+zip",
]


def clean_pdf_text(text):
    """
    Clean text extracted from PDFs with enhanced space handling.
    Preserves special characters like (, ), %, = that are valid in code/math.

    Args:
        text (str): The raw text extracted from a PDF
    Returns:
        str: Cleaned text with minimal necessary spacing
    """
    if not text:
        return text

    # Step 1: Normalize Unicode characters
    text = unicodedata.normalize("NFKC", text)

    # Step 2: Replace common PDF artifacts
    replacements = {
        # Common ligatures
        "ﬁ": "fi",
        "ﬂ": "fl",
        "ﬀ": "ff",
        "ﬃ": "ffi",
        "ﬄ": "ffl",
        # Quotation marks and apostrophes
        """: "'", """: "'",
        '"': '"',
        "′": "'",
        "‚": ",",
        "„": '"',
        # Dashes and hyphens
        "‒": "-",
        "–": "-",
        "—": "-",
        "―": "-",
        # Other common replacements
        "…": "...",
        "•": "*",
        "°": " degrees ",
        "¹": "1",
        "²": "2",
        "³": "3",
        "©": "(c)",
        "®": "(R)",
        "™": "(TM)",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # Step 3: Clean control characters while preserving essential whitespace and special chars
    text = "".join(
        char
        for char in text
        if unicodedata.category(char)[0] != "C"
        or char in "\n\t "
        or char in "()%=[]{}#$@!?.,;:+-*/^<>&|~"
    )

    # Step 4: Enhanced space cleaning
    text = re.sub(r"[ \t]+", " ", text)  # Consolidate horizontal whitespace
    text = re.sub(r" +\n", "\n", text)  # Remove spaces before newlines
    text = re.sub(r"\n +", "\n", text)  # Remove spaces after newlines
    text = re.sub(r"\n\t+", "\n", text)  # Remove tabs at start of lines
    text = re.sub(r"\t+\n", "\n", text)  # Remove tabs at end of lines
    text = re.sub(r"\t+", " ", text)  # Replace tabs with single space

    # Step 5: Remove empty lines while preserving paragraph structure
    text = re.sub(r"\n{3,}", "\n\n", text)  # Max two consecutive newlines
    text = re.sub(r"^\s+", "", text)  # Remove leading whitespace
    text = re.sub(r"\s+$", "", text)  # Remove trailing whitespace

    # Step 6: Clean up around punctuation
    text = re.sub(r"\s+([.,;:!?)])", r"\1", text)  # Remove spaces before punctuation
    text = re.sub(r"(\()\s+", r"\1", text)  # Remove spaces after opening parenthesis
    text = re.sub(
        r"\s+([.,])\s+", r"\1 ", text
    )  # Ensure single space after periods and commas

    # Step 7: Remove zero-width and invisible characters
    text = re.sub(r"[\u200b\u200c\u200d\ufeff\u200e\u200f]", "", text)

    # Step 8: Fix hyphenation and line breaks
    text = re.sub(
        r"(?<=\w)-\s*\n\s*(?=\w)", "", text
    )  # Remove hyphenation at line breaks

    return text.strip()


async def _extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    try:
        text = ""
        logger.debug(f"Found {len(doc)} pages in PDF")
        for page in doc:
            text += page.get_text()
        normalized_text = clean_pdf_text(text)
        return normalized_text
    finally:
        doc.close()


async def _extract_text_from_pdf(pdf_path):
    """Extract text from PDF asynchronously"""

    def _extract():
        doc = fitz.open(pdf_path)
        try:
            text = ""
            logger.debug(f"Found {len(doc)} pages in PDF")
            for page in doc:
                text += page.get_text()
            return clean_pdf_text(text)
        finally:
            doc.close()

    # Run CPU-bound PDF processing in a thread pool
    return await asyncio.get_event_loop().run_in_executor(None, _extract)


async def extract_pdf(state: ContentState):
    """
    Parse the PDF file and extract its content asynchronously.
    """
    return_dict = {}
    assert state.get("file_path"), "No file path provided"
    assert state.get("identified_type") in SUPPORTED_FITZ_TYPES, "Unsupported File Type"

    if (
        state.get("file_path") is not None
        and state.get("identified_type") in SUPPORTED_FITZ_TYPES
    ):
        file_path = state.get("file_path")
        try:
            text = await _extract_text_from_pdf(file_path)
            return_dict["content"] = text
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found at {file_path}")
        except Exception as e:
            raise Exception(f"An error occurred: {e}")

    return return_dict
