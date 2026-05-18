from open_notebook.multimodal.renderers.video_markdown import (
    render_video_understanding_markdown,
)
from open_notebook.multimodal.types import (
    VideoEntity,
    VideoTimelineSegment,
    VideoUnderstandingResult,
)


def test_render_video_understanding_markdown():
    result = VideoUnderstandingResult(
        summary="A short overview.",
        key_events=["Opening scene", "Key demonstration"],
        entities=[
            VideoEntity(name="Laser", entity_type="object", description="Bright beam")
        ],
        timeline=[
            VideoTimelineSegment(
                start_seconds=0,
                end_seconds=12,
                title="Intro",
                description="Presenter introduces the experiment.",
            )
        ],
        transcript_used=True,
        provider="openai_compatible",
        model="ep-demo",
    )

    markdown = render_video_understanding_markdown(result)

    assert "# Video Understanding" in markdown
    assert "## Overview" in markdown
    assert "Opening scene" in markdown
    assert "[00:00 - 00:12] Intro: Presenter introduces the experiment." in markdown
    assert "Laser (object): Bright beam" in markdown
