#!/usr/bin/env python3
"""Export productive OpenNotebook prompt and transformer defaults."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = ROOT / "exports" / "transformers"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def locate(path: str, text: str) -> tuple[int, int]:
    content = read(path)
    start = content.find(text)
    if start < 0:
        return 1, len(content.splitlines())
    line_start = content[:start].count("\n") + 1
    line_end = line_start + text.count("\n")
    return line_start, line_end


def whole_file(path: str) -> tuple[str, int, int]:
    text = read(path)
    return text, 1, len(text.splitlines())


def regex_extract(path: str, pattern: str) -> tuple[str, int, int]:
    content = read(path)
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        raise RuntimeError(f"Pattern not found in {path}: {pattern}")
    text = match.group(1)
    line_start, line_end = locate(path, text)
    return text, line_start, line_end


def transformation_prompt(name: str) -> Callable[[str], tuple[str, int, int]]:
    pattern = (
        r'name:\s+"'
        + re.escape(name)
        + r'".*?prompt:"(.*?)",\s*apply_default:'
    )
    return lambda path: regex_extract(path, pattern)


def episode_briefing(name: str) -> Callable[[str], tuple[str, int, int]]:
    pattern = (
        r'name:\s+"'
        + re.escape(name)
        + r'".*?default_briefing:\s+"(.*?)",'
    )
    return lambda path: regex_extract(path, pattern)


def speaker_profile(name: str) -> Callable[[str], tuple[str, int, int]]:
    def extract(path: str) -> tuple[str, int, int]:
        content = read(path)
        speaker_section = content.find("insert into speaker_profile")
        if speaker_section < 0:
            raise RuntimeError(f"Speaker profile section not found in {path}")
        start = content.find(f'{{\n                name: "{name}"', speaker_section)
        if start < 0:
            raise RuntimeError(f"Speaker profile not found in {path}: {name}")

        depth = 0
        end = start
        in_string = False
        escape = False
        for index, char in enumerate(content[start:], start=start):
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break

        text = content[start:end]
        line_start, line_end = locate(path, text)
        return text, line_start, line_end

    return extract


def default_transformation_prompt(path: str) -> tuple[str, int, int]:
    return regex_extract(path, r'CONTENT\s+\{transformation_instructions:\s+"(.*?)"\};')


def title_prompt(path: str) -> tuple[str, int, int]:
    text = (
        "Erstelle auf Grundlage der folgenden Notiz einen prägnanten "
        "deutschen Titel mit maximal 15 Wörtern."
    )
    content = read(path)
    marker = '"Erstelle auf Grundlage der folgenden Notiz'
    start = content.find(marker)
    if start < 0:
        raise RuntimeError(f"Title prompt not found in {path}")
    line_start = content[:start].count("\n") + 1
    line_end = line_start + 3
    return text, line_start, line_end


ENTRY_SPECS = [
    {
        "name": "Ask Search Strategy",
        "identifier": "ask/entry",
        "file_path": "prompts/ask/entry.jinja",
        "type": "Prompt-Template",
        "format": "Jinja2",
        "purpose": "Erzeugt aus einer Nutzerfrage eine JSON-Suchstrategie fuer die Recherche.",
        "confidence": "sicher",
        "extractor": whole_file,
    },
    {
        "name": "Ask Query Processing",
        "identifier": "ask/query_process",
        "file_path": "prompts/ask/query_process.jinja",
        "type": "Prompt-Template",
        "format": "Jinja2",
        "purpose": "Beantwortet eine einzelne Suchanfrage anhand gefundener Quellen mit Zitierregeln.",
        "confidence": "sicher",
        "extractor": whole_file,
    },
    {
        "name": "Ask Final Answer",
        "identifier": "ask/final_answer",
        "file_path": "prompts/ask/final_answer.jinja",
        "type": "Prompt-Template",
        "format": "Jinja2",
        "purpose": "Synthetisiert Teilantworten zu einer finalen Antwort mit Quellenverweisen.",
        "confidence": "sicher",
        "extractor": whole_file,
    },
    {
        "name": "Notebook Chat System Prompt",
        "identifier": "chat/system",
        "file_path": "prompts/chat/system.jinja",
        "type": "Prompt-Template",
        "format": "Jinja2",
        "purpose": "Systemprompt fuer allgemeine Notebook-Konversationen mit optionalem Kontext.",
        "confidence": "sicher",
        "extractor": whole_file,
    },
    {
        "name": "Source Chat System Prompt",
        "identifier": "source_chat/system",
        "file_path": "prompts/source_chat/system.jinja",
        "type": "Prompt-Template",
        "format": "Jinja2",
        "purpose": "Systemprompt fuer source-spezifische Analysegespraeche.",
        "confidence": "sicher",
        "extractor": whole_file,
    },
    {
        "name": "Podcast Outline Prompt",
        "identifier": "podcast/outline",
        "file_path": "prompts/podcast/outline.jinja",
        "type": "Prompt-Template",
        "format": "Jinja2",
        "purpose": "Erzeugt eine Podcast-Gliederung als JSON.",
        "confidence": "sicher",
        "extractor": whole_file,
    },
    {
        "name": "Podcast Transcript Prompt",
        "identifier": "podcast/transcript",
        "file_path": "prompts/podcast/transcript.jinja",
        "type": "Prompt-Template",
        "format": "Jinja2",
        "purpose": "Erzeugt Segment-Transkripte fuer Podcast-Audio als JSON.",
        "confidence": "sicher",
        "extractor": whole_file,
    },
    *[
        {
            "name": title,
            "identifier": identifier,
            "file_path": "open_notebook/database/migrations/5.surrealql",
            "type": "Transformer / Seed",
            "format": "SurrealQL Datenbank-Seed",
            "purpose": purpose,
            "confidence": "sicher",
            "extractor": transformation_prompt(identifier),
        }
        for title, identifier, purpose in [
            ("Paper Analysis", "Analyze Paper", "Analysiert wissenschaftliche und fachliche Texte."),
            ("Key Insights", "Key Insights", "Extrahiert zentrale Erkenntnisse."),
            ("Dense Summary", "Dense Summary", "Erstellt eine dichte Zusammenfassung."),
            ("Reflection Questions", "Reflections", "Erzeugt Reflexionsfragen."),
            ("Table of Contents", "Table of Contents", "Erstellt ein Inhaltsverzeichnis."),
            ("Simple Summary", "Simple Summary", "Erzeugt eine Kurzzusammenfassung."),
        ]
    ],
    {
        "name": "Default Transformation Instructions",
        "identifier": "open_notebook:default_prompts.transformation_instructions",
        "file_path": "open_notebook/database/migrations/5.surrealql",
        "type": "Prompt / Seed",
        "format": "SurrealQL Datenbank-Seed",
        "purpose": "Globaler Zusatzprompt vor Transformationen.",
        "confidence": "sicher",
        "extractor": default_transformation_prompt,
    },
    *[
        {
            "name": f"Podcast Episode Briefing: {identifier}",
            "identifier": identifier,
            "file_path": "open_notebook/database/migrations/7.surrealql",
            "type": "Podcast Template / Seed",
            "format": "SurrealQL Datenbank-Seed",
            "purpose": purpose,
            "confidence": "sicher",
            "extractor": episode_briefing(identifier),
        }
        for identifier, purpose in [
            ("tech_discussion", "Technische Diskussion"),
            ("solo_expert", "Experten-Erklaerung"),
            ("business_analysis", "Business-Analyse"),
        ]
    ],
    *[
        {
            "name": f"Podcast Speaker Profile: {identifier}",
            "identifier": identifier,
            "file_path": "open_notebook/database/migrations/7.surrealql",
            "type": "Podcast Persona Template / Seed",
            "format": "SurrealQL Datenbank-Seed",
            "purpose": "Sprecherprofil fuer Podcast-Generierung.",
            "confidence": "wahrscheinlich",
            "extractor": speaker_profile(identifier),
        }
        for identifier in ["tech_experts", "solo_expert", "business_panel"]
    ],
    {
        "name": "AI Note Title Prompt",
        "identifier": "api.routers.notes.create_note.title_prompt",
        "file_path": "api/routers/notes.py",
        "type": "Prompt",
        "format": "Python",
        "purpose": "Generiert automatisch einen kurzen Titel fuer AI-Notizen ohne Titel.",
        "confidence": "sicher",
        "extractor": title_prompt,
    },
]


def build_entries() -> list[dict[str, object]]:
    entries = []
    for spec in ENTRY_SPECS:
        extractor = spec["extractor"]
        file_path = str(spec["file_path"])
        prompt, line_start, line_end = extractor(file_path)
        entry = {
            "name": spec["name"],
            "identifier": spec["identifier"],
            "file_path": file_path,
            "line_start": line_start,
            "line_end": line_end,
            "location": f"{file_path}:{line_start}",
            "type": spec["type"],
            "format": spec["format"],
            "purpose": spec["purpose"],
            "confidence": spec["confidence"],
            "original_prompt": prompt,
            "original_text": prompt,
            "notes": "",
        }
        entries.append(entry)
    return entries


def write_json(entries: list[dict[str, object]], created_at: str) -> None:
    payload = {
        "created_at": created_at,
        "repository_root": str(ROOT),
        "count": len(entries),
        "entries": entries,
    }
    (EXPORT_DIR / "transformers-export.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_markdown(entries: list[dict[str, object]], created_at: str) -> None:
    lines = [
        "# Transformers Export",
        "",
        f"Erstellt am: {created_at}",
        "",
    ]
    for entry in entries:
        lines.extend(
            [
                f"## {entry['name']}",
                "",
                f"**Identifier:** {entry['identifier']}",
                "",
                f"**Fundort:** {entry['file_path']}:{entry['line_start']}-{entry['line_end']}",
                "",
                f"**Typ:** {entry['type']}",
                "",
                f"**Format / Struktur:** {entry['format']}",
                "",
                f"**Zweck:** {entry['purpose']}",
                "",
                f"**Sicherheit:** {entry['confidence']}",
                "",
                "````text",
                str(entry["original_prompt"]),
                "````",
                "",
            ]
        )
    (EXPORT_DIR / "transformers-export.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc).isoformat()
    entries = build_entries()
    write_json(entries, created_at)
    write_markdown(entries, created_at)
    print(f"Exported {len(entries)} transformer prompts to {EXPORT_DIR}")


if __name__ == "__main__":
    main()
