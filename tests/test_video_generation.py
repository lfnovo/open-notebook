import pytest

from open_notebook.podcasts.models import PodcastEpisode
from open_notebook.podcasts.video_generation import (
    DEFAULT_CANVAS,
    build_storyboard,
    patch_storyboard_item,
)
from open_notebook.podcasts.video_presets import (
    DEFAULT_VIDEO_STYLE_PRESET,
    get_video_style_preset,
    list_video_style_presets,
)


def _episode_with_transcript(turns: int = 12) -> PodcastEpisode:
    transcript = {
        "transcript": [
            {
                "speaker": "Host",
                "dialogue": (
                    "Тимлид часто спасает сделку вместо того, чтобы развивать навык. "
                    "Важно увидеть цифру, причину, зону контроля и следующее действие."
                ),
            }
            for _ in range(turns)
        ]
    }
    return PodcastEpisode(
        name="Роль тимлида",
        episode_profile={},
        speaker_profile={},
        briefing="",
        content="",
        audio_file=None,
        transcript=transcript,
    )


def test_video_style_presets_are_codex_configurable():
    preset = get_video_style_preset(DEFAULT_VIDEO_STYLE_PRESET)

    assert preset.image_prompt_template == "image_prompt_whiteboard.jinja"
    assert preset.target_scene_seconds["balanced"] < 25
    assert any(item["name"] == DEFAULT_VIDEO_STYLE_PRESET for item in list_video_style_presets())


@pytest.mark.asyncio
async def test_storyboard_builds_frequent_full_slide_prompts(monkeypatch):
    async def no_llm(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "open_notebook.podcasts.video_generation._call_storyboard_llm", no_llm
    )
    monkeypatch.setattr(
        "open_notebook.podcasts.video_generation._entry_durations",
        lambda episode, entries: [10.0 for _ in entries],
    )

    storyboard = await build_storyboard(
        episode=_episode_with_transcript(),
        briefing="Сделай видео в стиле NotebookLM whiteboard explainer.",
        language_model_id=None,
        scene_density="balanced",
        canvas=DEFAULT_CANVAS,
        style_preset=DEFAULT_VIDEO_STYLE_PRESET,
    )

    assert storyboard["style_preset"] == DEFAULT_VIDEO_STYLE_PRESET
    assert len(storyboard["items"]) >= 6
    first = storyboard["items"][0]
    assert "overlay" not in first
    assert first["exact_text"]
    assert first["image_prompt"] == first["visual_prompt"]
    assert "No external text overlay" in first["image_prompt"]
    assert first["exact_text"][0] in first["image_prompt"]
    assert "Do not copy narration" in first["image_prompt"]


@pytest.mark.asyncio
async def test_storyboard_rejects_truncated_or_long_visible_text(monkeypatch):
    async def noisy_llm(scenes, *args, **kwargs):
        return [
            {
                "title": "Плохой текст",
                "slide_type": "metaphor",
                "narration_summary": "Тимлид часто спасает сделку вместо развития навыка.",
                "learning_intent": "Показать разницу между помощью и подменой роли.",
                "visual_concept": "Тимлид выбирает между тушением пожара и тренировкой навыка.",
                "text_strategy": "Короткий контраст вместо пересказа озвучки.",
                "exact_text": [
                    "Часто результат команды держится исключительно на ваших личных усилиях...",
                    "Но в долгосрочной перспективе это создает опасн...",
                ],
                "visual_instruction": "Покажи контраст двух управленческих позиций.",
            }
            for _ in scenes
        ]

    monkeypatch.setattr(
        "open_notebook.podcasts.video_generation._call_storyboard_llm", noisy_llm
    )
    monkeypatch.setattr(
        "open_notebook.podcasts.video_generation._entry_durations",
        lambda episode, entries: [10.0 for _ in entries],
    )

    storyboard = await build_storyboard(
        episode=_episode_with_transcript(),
        briefing="Сделай видео в стиле NotebookLM whiteboard explainer.",
        language_model_id=None,
        scene_density="balanced",
        canvas=DEFAULT_CANVAS,
        style_preset=DEFAULT_VIDEO_STYLE_PRESET,
    )

    first = storyboard["items"][0]

    assert first["visual_concept"]
    assert first["text_strategy"]
    assert first["exact_text"] == ["Не спасать", "Развивать навык"]
    assert all("..." not in item and "…" not in item for item in first["exact_text"])


@pytest.mark.asyncio
async def test_patch_storyboard_item_rebuilds_prompt_from_source_fields(monkeypatch):
    class FakeVideo:
        def __init__(self):
            self.storyboard = {
                "style_preset": DEFAULT_VIDEO_STYLE_PRESET,
                "items": [
                    {
                        "id": "scene-001",
                        "asset_id": "asset-scene-001-v1",
                        "slide_type": "metaphor",
                        "narration_summary": "Старая озвучка",
                        "learning_intent": "Старый смысл",
                        "visual_concept": "Старый концепт",
                        "text_strategy": "Старая стратегия",
                        "exact_text": ["Старый текст"],
                        "visual_instruction": "Старая композиция",
                        "image_prompt": "OLD PROMPT",
                        "visual_prompt": "OLD PROMPT",
                        "duration": 10.0,
                    }
                ],
            }
            self.status = "completed"
            self.saved = False

        async def save(self):
            self.saved = True

    video = FakeVideo()

    async def fake_get(video_id):
        return video

    monkeypatch.setattr(
        "open_notebook.podcasts.video_generation.EpisodeVideo.get", fake_get
    )

    updated = await patch_storyboard_item(
        "episode_video:test",
        "scene-001",
        {
            "exact_text": ["Не спасать", "Развивать навык"],
            "visual_instruction": "Новая композиция про тренировку навыка.",
        },
    )

    item = updated.storyboard["items"][0]

    assert video.saved
    assert updated.status == "storyboard_edited"
    assert item["image_prompt"] == item["visual_prompt"]
    assert item["image_prompt"] != "OLD PROMPT"
    assert "Не спасать" in item["image_prompt"]
    assert "Развивать навык" in item["image_prompt"]
    assert "Новая композиция" in item["image_prompt"]
