"""PDF and Office document processing utilities."""
import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from loguru import logger


def calculate_page_params(total_pages: int) -> Tuple[int, int]:
    """
    Calculate adaptive sampling for PDF pages (similar to video frame sampling).

    | Pages     | Sample Rate | Max Pages | Coverage         |
    |-----------|-------------|-----------|------------------|
    | <= 20     | every page  | 20        | All pages        |
    | 21-100    | every 2nd   | 50        | Every 2nd page   |
    | 101-500   | every 5th   | 100       | Every 5th page   |
    | > 500     | every 10th  | 100       | Every 10th page  |

    Args:
        total_pages: Total number of pages in the PDF

    Returns:
        Tuple of (step_size, max_pages)
    """
    if total_pages <= 20:
        return (1, 20)
    elif total_pages <= 100:
        return (2, 50)
    elif total_pages <= 500:
        return (5, 100)
    else:
        return (10, 100)


async def get_pdf_page_count(file_path: str) -> int:
    """
    Get the number of pages in a PDF file using pdfinfo (from poppler).

    Args:
        file_path: Path to the PDF file

    Returns:
        Number of pages

    Raises:
        RuntimeError: If pdfinfo fails
    """
    cmd = ["pdfinfo", file_path]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"pdfinfo failed: {stderr.decode()}")

    # Parse output for "Pages:" line
    for line in stdout.decode().split("\n"):
        if line.startswith("Pages:"):
            return int(line.split(":")[1].strip())

    raise RuntimeError("Could not determine page count from pdfinfo output")


async def convert_pdf_to_images(
    file_path: str,
    dpi: int = 150,
    output_dir: Optional[str] = None,
) -> List[Tuple[str, int]]:
    """
    Convert PDF pages to images using pdftoppm (from poppler).

    Uses adaptive sampling based on page count to limit API costs.

    Args:
        file_path: Path to the PDF file
        dpi: DPI for rendering (default 150, balances quality and size)
        output_dir: Directory to save images (creates temp dir if None)

    Returns:
        List of (image_path, page_number) tuples for selected pages
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="pdf_pages_")

    try:
        # Get total page count
        total_pages = await get_pdf_page_count(file_path)
        logger.info(f"PDF has {total_pages} pages")

        # Calculate sampling parameters
        step_size, max_pages = calculate_page_params(total_pages)
        logger.info(
            f"Using step_size={step_size}, max_pages={max_pages} for {total_pages} pages"
        )

        # Determine which pages to convert
        pages_to_convert = []
        for i in range(1, total_pages + 1, step_size):
            pages_to_convert.append(i)
            if len(pages_to_convert) >= max_pages:
                break

        logger.info(f"Converting {len(pages_to_convert)} pages from PDF")

        # Convert selected pages using pdftoppm
        results = []
        for page_num in pages_to_convert:
            output_prefix = os.path.join(output_dir, f"page_{page_num:04d}")
            cmd = [
                "pdftoppm",
                "-png",
                "-r",
                str(dpi),
                "-f",
                str(page_num),
                "-l",
                str(page_num),
                file_path,
                output_prefix,
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.warning(f"pdftoppm failed for page {page_num}: {stderr.decode()}")
                continue

            # Find the output file (pdftoppm adds page number suffix)
            output_files = list(Path(output_dir).glob(f"page_{page_num:04d}*.png"))
            if output_files:
                results.append((str(output_files[0]), page_num))

        logger.info(f"Successfully converted {len(results)} PDF pages to images")
        return results

    except Exception as e:
        logger.error(f"PDF conversion failed: {e}")
        # Cleanup on failure
        if output_dir and os.path.isdir(output_dir):
            shutil.rmtree(output_dir, ignore_errors=True)
        raise


async def convert_office_to_pdf(file_path: str) -> str:
    """
    Convert Office documents (docx, xlsx, pptx, etc.) to PDF using LibreOffice.

    Args:
        file_path: Path to the Office document

    Returns:
        Path to the temporary PDF file

    Raises:
        RuntimeError: If conversion fails
    """
    # Create temp directory for output
    output_dir = tempfile.mkdtemp(prefix="office_convert_")

    try:
        # Use LibreOffice headless mode
        cmd = [
            "soffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            output_dir,
            file_path,
        ]

        logger.info(f"Converting Office document to PDF: {file_path}")

        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"LibreOffice conversion failed: {stderr.decode()}")

        # Find the output PDF (LibreOffice names it based on input filename)
        pdf_files = list(Path(output_dir).glob("*.pdf"))

        if not pdf_files:
            raise RuntimeError(
                f"No PDF output found after conversion of {file_path}"
            )

        pdf_path = str(pdf_files[0])
        logger.info(f"Successfully converted to PDF: {pdf_path}")
        return pdf_path

    except Exception as e:
        # Cleanup on failure
        if os.path.isdir(output_dir):
            shutil.rmtree(output_dir, ignore_errors=True)
        raise RuntimeError(f"Office to PDF conversion failed: {e}") from e


def cleanup_pdf_temp_files(paths: List[str]) -> None:
    """
    Remove temporary files and directories created during PDF processing.

    Args:
        paths: List of file or directory paths to remove
    """
    for path in paths:
        if path is None:
            continue
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
                logger.debug(f"Removed temp directory: {path}")
            elif os.path.isfile(path):
                os.unlink(path)
                logger.debug(f"Removed temp file: {path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {path}: {e}")
