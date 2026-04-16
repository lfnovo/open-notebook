"""
Microsoft Word .doc file processor
Handles legacy .doc format (not .docx which is handled by content-core)
"""

import subprocess
from pathlib import Path
from typing import Optional

from loguru import logger


def extract_text_from_doc(doc_path: str) -> str:
        raise


def is_doc_file(file_path: str) -> bool:
    """
    Check if file is a legacy .doc file (not .docx).
    
    Args:
        file_path: Path to check
        
    Returns:
        True if file is .doc format
    """
    return file_path.lower().endswith('.doc') and not file_path.lower().endswith('.docx')