"""Turn a user-written script (plain text or Markdown) into podcast dialogue.

The script is read as written: no model rewrites it. Markdown syntax is
stripped so the voice doesn't read symbols aloud, each paragraph becomes one
clip, and a line starting with a speaker name from the chosen profile
(``Max: ...`` or ``**Max:** ...``) switches to that speaker's voice. Text
before any label is read by the profile's first speaker.
"""

import re
from typing import Dict, List

# Clips longer than this are split at sentence ends; some TTS providers cap a
# single request well below a long paragraph (OpenAI 4096, ElevenLabs 5000).
MAX_CLIP_CHARS = 1500

_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
_HR_RE = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")
_LABEL_RE = re.compile(r"^\**\s*([^:*\n]{1,60}?)\s*\**\s*:\s*\**\s*(.*)$")
_SENTENCE_END_RE = re.compile(r"(?<=[.!?…])\s+")


def _clean_line(line: str) -> str:
    line = re.sub(r"<[^>]+>", " ", line)  # HTML tags
    line = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", line)  # images
    line = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)  # links -> text
    line = re.sub(r"^\s{0,3}#{1,6}\s*", "", line)  # headings
    line = re.sub(r"^\s*>+\s?", "", line)  # blockquotes
    line = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", line)  # list markers
    line = re.sub(r"(\*\*|__|\*|_|~~|`)(?=\S)(.+?)(?<=\S)\1", r"\2", line)
    line = line.replace("`", "")
    return re.sub(r"\s+", " ", line).strip()


def _split_long(text: str, limit: int = MAX_CLIP_CHARS) -> List[str]:
    if len(text) <= limit:
        return [text]
    chunks: List[str] = []
    current = ""
    for sentence in _SENTENCE_END_RE.split(text):
        while len(sentence) > limit:  # one huge sentence: cut at a space
            cut = sentence.rfind(" ", 0, limit)
            if cut <= 0:
                cut = limit
            if current:
                chunks.append(current)
                current = ""
            chunks.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        if not sentence:
            continue
        if current and len(current) + 1 + len(sentence) > limit:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}" if current else sentence
    if current:
        chunks.append(current)
    return chunks


def parse_script(text: str, speaker_names: List[str]) -> List[Dict[str, str]]:
    """Return ``[{"speaker", "dialogue"}, ...]`` clips for ``text``.

    Raises ValueError when there is nothing to read or no speakers.
    """
    if not speaker_names:
        raise ValueError("The speaker profile has no speakers")
    by_lower = {name.strip().lower(): name for name in speaker_names}
    speaker = speaker_names[0]

    text = _FRONTMATTER_RE.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))

    paragraphs: List[tuple[str, str]] = []
    para_speaker = speaker
    para_lines: List[str] = []

    def flush() -> None:
        body = " ".join(para_lines).strip()
        if body:
            paragraphs.append((para_speaker, body))
        para_lines.clear()

    for raw in text.split("\n"):
        if not raw.strip() or _HR_RE.match(raw):
            flush()
            continue
        line = raw
        label = _LABEL_RE.match(raw.strip())
        if label and label.group(1).strip().lower() in by_lower:
            flush()
            speaker = by_lower[label.group(1).strip().lower()]
            line = label.group(2)
        if para_lines and speaker != para_speaker:
            flush()
        para_speaker = speaker
        cleaned = _clean_line(line)
        if cleaned:
            para_lines.append(cleaned)
    flush()

    turns = [
        {"speaker": who, "dialogue": chunk}
        for who, body in paragraphs
        for chunk in _split_long(body)
    ]
    if not turns:
        raise ValueError("The script has no text to read")
    return turns
