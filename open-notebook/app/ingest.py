from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from config import Settings, get_settings
from rag import add_documents, chunk_text


SUPPORTED_SUFFIXES = {".txt", ".md", ".html", ".htm", ".pdf"}


def extract_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = _extract_pdf_with_pdfplumber(path)
        return text or _extract_pdf_with_pypdf2(path)
    if suffix in {".txt", ".md", ".html", ".htm"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError(f"Unsupported file type: {path.suffix}")


def _extract_pdf_with_pdfplumber(path: Path) -> str:
    chunks: list[str] = []
    try:
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                chunks.append(page.extract_text() or "")
    except Exception:
        return ""
    return "\n".join(chunks).strip()


def _extract_pdf_with_pypdf2(path: Path) -> str:
    from PyPDF2 import PdfReader

    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages).strip()


def build_documents(text: str, source: str, settings: Settings) -> list[dict[str, str]]:
    docs: list[dict[str, str]] = []
    for idx, piece in enumerate(chunk_text(text, settings.chunk_size, settings.chunk_overlap)):
        docs.append(
            {
                "source": source,
                "chunk_id": f"chunk-{idx}",
                "chunk_text": piece,
                "snippet": piece[:240].replace("\n", " ").strip(),
            }
        )
    return docs


def ingest_text(text: str, source: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    documents = build_documents(text, source, settings)
    result = add_documents(documents, settings=settings)
    result["source"] = source
    return result


def ingest_file(path: Path, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    text = extract_text_from_file(path)
    return ingest_text(text, path.name, settings=settings)


def ingest_dir(directory: Path, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    summary = {"files": 0, "chunks_added": 0, "sources": []}
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        result = ingest_file(path, settings=settings)
        summary["files"] += 1
        summary["chunks_added"] += result["chunks_added"]
        summary["sources"].append(result["source"])
    return summary


def ingest_youtube(url: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    with tempfile.TemporaryDirectory() as tmpdir:
        output_template = str(Path(tmpdir) / "%(id)s.%(ext)s")
        subprocess.run(
            ["yt-dlp", "-x", "--audio-format", "mp3", "-o", output_template, url],
            check=True,
        )
        audio_files = sorted(Path(tmpdir).glob("*.mp3"))
        if not audio_files:
            raise RuntimeError("yt-dlp completed but no audio file was produced")
        transcript = transcribe_audio(audio_files[0])
    return ingest_text(transcript, url, settings=settings)


def transcribe_audio(path: Path) -> str:
    import whisper

    model = whisper.load_model("tiny")
    output = model.transcribe(str(path))
    text = output.get("text", "").strip()
    if not text:
        raise RuntimeError("Whisper returned an empty transcript")
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest content into the Open Notebook prototype")
    subparsers = parser.add_subparsers(dest="command", required=True)

    dir_parser = subparsers.add_parser("ingest_dir")
    dir_parser.add_argument("--dir", required=True, dest="directory")

    file_parser = subparsers.add_parser("ingest_file")
    file_parser.add_argument("--path", required=True)

    youtube_parser = subparsers.add_parser("ingest_youtube")
    youtube_parser.add_argument("--url", required=True)

    args = parser.parse_args()
    settings = get_settings()

    if args.command == "ingest_dir":
        result = ingest_dir(Path(args.directory), settings=settings)
    elif args.command == "ingest_file":
        result = ingest_file(Path(args.path), settings=settings)
    else:
        result = ingest_youtube(args.url, settings=settings)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
