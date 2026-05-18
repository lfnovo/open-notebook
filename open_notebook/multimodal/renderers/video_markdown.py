from open_notebook.multimodal.types import VideoUnderstandingResult


def _format_timestamp(seconds: float | None) -> str:
    if seconds is None:
        return ""
    total = int(seconds)
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def render_video_understanding_markdown(result: VideoUnderstandingResult) -> str:
    lines = [
        "# Video Understanding",
        "",
        "## Overview",
        result.summary.strip(),
        "",
        "## Analysis Metadata",
        f"- Provider: {result.provider}",
        f"- Model: {result.model}",
        f"- Transcript used: {'yes' if result.transcript_used else 'no'}",
        "",
    ]

    if result.key_events:
        lines.extend(["## Key Events"])
        lines.extend(f"- {event}" for event in result.key_events)
        lines.append("")

    if result.timeline:
        lines.extend(["## Timeline"])
        for segment in result.timeline:
            start = _format_timestamp(segment.start_seconds)
            end = _format_timestamp(segment.end_seconds)
            prefix = ""
            if start or end:
                prefix = f"[{start or '--'} - {end or '--'}] "
            title = f"{segment.title}: " if segment.title else ""
            lines.append(f"- {prefix}{title}{segment.description}")
        lines.append("")

    if result.entities:
        lines.extend(["## Entities"])
        for entity in result.entities:
            detail = f" ({entity.entity_type})" if entity.entity_type else ""
            description = f": {entity.description}" if entity.description else ""
            lines.append(f"- {entity.name}{detail}{description}")
        lines.append("")

    return "\n".join(lines).strip()
