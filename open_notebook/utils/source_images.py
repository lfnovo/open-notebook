"""Read-only raster presentation of retained source files, independent of OCR."""

import base64
import threading
from contextlib import closing
from io import BytesIO
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageOps

from open_notebook.config import UPLOADS_FOLDER
from open_notebook.domain.notebook import Source
from open_notebook.exceptions import InvalidInputError
from open_notebook.utils.chat_images import ChatImage

# PDFium is not thread-safe, even for distinct documents.
_PDF_LOCK = threading.Lock()


def source_file(source: Source) -> Path:
    if not source.asset or not source.asset.file_path:
        raise InvalidInputError("This source has no retained PDF or image file.")
    path = Path(source.asset.file_path).resolve()
    if not path.is_relative_to(Path(UPLOADS_FOLDER).resolve()):
        raise InvalidInputError("Source file is outside the uploads directory.")
    if not path.is_file():
        raise InvalidInputError(
            "The original file is unavailable. Re-upload it with file retention enabled to use crops."
        )
    if path.stat().st_size > 100 * 1024 * 1024:
        raise InvalidInputError("Visual inspection supports files up to 100 MB.")
    return path


def inspect_source(source: Source, query: str = "", start_page: int = 1) -> dict:
    path = source_file(source)
    if path.suffix.lower() != ".pdf":
        return {
            "pages": 1,
            "matches": [{"page": 1, "text": source.title or "Image source"}],
        }
    with _PDF_LOCK, pdfium.PdfDocument(str(path)) as document:
        if start_page < 1 or start_page > len(document):
            raise InvalidInputError("Page is outside the document.")
        matches = []
        # Bounded batches let a model locate figures without loading a huge PDF.
        end = min(len(document), start_page + 39)
        for index in range(start_page - 1, end):
            with (
                closing(document[index]) as page,
                closing(page.get_textpage()) as textpage,
            ):
                text = textpage.get_text_range()
            offset = text.casefold().find(query.casefold()) if query else 0
            if offset >= 0:
                matches.append(
                    {
                        "page": index + 1,
                        "text": text[max(0, offset - 200) : offset + 800],
                    }
                )
                if len(matches) == 10:
                    break
        return {"pages": len(document), "matches": matches, "scanned_until": index + 1}


def render_source_image(
    source: Source, page_number: int, box: list[float] | None = None
) -> ChatImage:
    path = source_file(source)
    if page_number < 1:
        raise InvalidInputError("Page numbers start at 1.")
    if box is not None and (
        len(box) != 4
        or not all(0 <= n <= 1 for n in box)
        or box[0] >= box[2]
        or box[1] >= box[3]
    ):
        raise InvalidInputError(
            "Crop must be [left, top, right, bottom] fractions between 0 and 1."
        )
    if path.suffix.lower() == ".pdf":
        with _PDF_LOCK, pdfium.PdfDocument(str(path)) as document:
            if page_number > len(document):
                raise InvalidInputError("Page is outside the document.")
            with closing(document[page_number - 1]) as page:
                width, height = page.get_size()
                if width <= 0 or height <= 0:
                    raise InvalidInputError("Invalid PDF page size.")
                bitmap = page.render(scale=min(2, 1800 / max(width, height)))
                try:
                    image = bitmap.to_pil().convert("RGB")
                finally:
                    bitmap.close()
    else:
        if page_number != 1:
            raise InvalidInputError("Image sources have only one page.")
        with Image.open(path) as original:
            if original.width * original.height > 25_000_000:
                raise InvalidInputError(
                    "Source images must be no larger than 25 megapixels."
                )
            image = ImageOps.exif_transpose(original).convert("RGB")
        image.thumbnail((1800, 1800))
    if box is not None:
        coordinates = [
            round(box[0] * image.width),
            round(box[1] * image.height),
            round(box[2] * image.width),
            round(box[3] * image.height),
        ]
        if coordinates[2] <= coordinates[0] or coordinates[3] <= coordinates[1]:
            raise InvalidInputError("The crop is too small.")
        image = image.crop(tuple(coordinates))
    output = BytesIO()
    image.save(output, format="PNG")
    return ChatImage(
        name=f"{source.title or 'Source'} · {page_number}"[:255],
        data_url="data:image/png;base64,"
        + base64.b64encode(output.getvalue()).decode(),
        kind="source",
        source_id=source.id,
        source_title=source.title,
        page=page_number,
    )
