from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import HTTPException

from api.routers.podcasts import (
    _asset_to_response,
    _video_to_response,
    stream_episode_video_asset_file,
)
from api.video_service import VideoService
from open_notebook.ai.connection_tester import (
    test_individual_model as _test_individual_model,
)
from open_notebook.ai.models import Model
from open_notebook.podcasts import audio_paths, video_paths
from open_notebook.podcasts.models import PodcastEpisode
from open_notebook.podcasts.video_generation import (
    DEFAULT_CANVAS,
    _episode_base_dir,
    build_storyboard,
    generate_openai_image,
    patch_storyboard_item,
)
from open_notebook.podcasts.video_paths import resolve_contained_video_path
from open_notebook.podcasts.video_presets import (
    DEFAULT_VIDEO_STYLE_PRESET,
    get_video_style_preset,
    list_video_style_presets,
)


def _video_root(tmp_path, monkeypatch):
    podcasts_root = tmp_path / "podcasts"
    monkeypatch.setattr(audio_paths, "PODCASTS_FOLDER", str(podcasts_root))
    root = podcasts_root / "videos"
    root.mkdir(parents=True, exist_ok=True)
    return root


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
    assert any(
        item["name"] == DEFAULT_VIDEO_STYLE_PRESET
        for item in list_video_style_presets()
    )


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


def test_asset_response_exposes_download_url_for_existing_file(tmp_path, monkeypatch):
    asset_path = _video_root(tmp_path, monkeypatch) / "video-1/assets/scene-001.png"
    asset_path.parent.mkdir(parents=True)
    asset_path.write_bytes(b"image")
    video = SimpleNamespace(id="episode_video:test")

    response = _asset_to_response(
        video,
        {
            "id": "asset-scene-001-v1",
            "path": str(asset_path),
        },
    )

    assert response["file_url"] == (
        "/api/podcasts/videos/episode_video%3Atest/assets/asset-scene-001-v1/file"
    )
    assert "path" not in response


def test_video_response_omits_internal_filesystem_paths(tmp_path, monkeypatch):
    asset_path = _video_root(tmp_path, monkeypatch) / "video-1/assets/scene.png"
    video_path = asset_path.parents[1] / "renders/final.mp4"
    asset_path.parent.mkdir(parents=True)
    video_path.parent.mkdir(parents=True)
    asset_path.write_bytes(b"image")
    video_path.write_bytes(b"video")
    video = SimpleNamespace(
        id="episode_video:test",
        name="Test video",
        episode="episode:test",
        status="completed",
        video_file=str(video_path),
        storyboard={"items": [{"id": "scene-1", "asset_path": str(asset_path)}]},
        assets=[{"id": "asset-1", "path": str(asset_path)}],
        settings={"output_dir": str(video_path.parents[1]), "aspect_ratio": "16:9"},
        usage={},
        error_message=None,
        created=None,
    )

    response = _video_to_response(video)

    assert response.video_file is None
    assert response.video_url is not None
    assert "path" not in response.assets[0]
    assert response.storyboard is not None
    assert "asset_path" not in response.storyboard["items"][0]
    assert "output_dir" not in response.settings


@pytest.mark.asyncio
async def test_asset_file_endpoint_streams_registered_asset(tmp_path, monkeypatch):
    asset_path = _video_root(tmp_path, monkeypatch) / "video-1/assets/scene-001.png"
    asset_path.parent.mkdir(parents=True)
    asset_path.write_bytes(b"image")
    video = SimpleNamespace(
        assets=[
            {
                "id": "asset-scene-001-v1",
                "path": str(asset_path),
            }
        ]
    )

    async def fake_get(video_id):
        assert video_id == "episode_video:test"
        return video

    monkeypatch.setattr("api.routers.podcasts.VideoService.get", fake_get)

    response = await stream_episode_video_asset_file(
        "episode_video:test", "asset-scene-001-v1"
    )

    assert response.path == asset_path
    assert response.media_type == "image/png"


def test_video_path_maps_known_legacy_data_roots(tmp_path, monkeypatch):
    expected = _video_root(tmp_path, monkeypatch) / "legacy/renders/final-v1.mp4"
    expected.parent.mkdir(parents=True)
    expected.write_bytes(b"video")
    monkeypatch.setattr(video_paths, "_existing_legacy_video_roots", lambda: ())

    assert resolve_contained_video_path(
        "notebook_data/podcasts/videos/legacy/renders/final-v1.mp4"
    ) == expected.resolve()
    assert resolve_contained_video_path(
        "/app/data/podcasts/videos/legacy/renders/final-v1.mp4"
    ) == expected.resolve()
    assert resolve_contained_video_path("file:///etc/hosts") is None
    assert resolve_contained_video_path("videos/../../outside") is None


def test_video_path_reads_existing_allowlisted_legacy_root(tmp_path, monkeypatch):
    _video_root(tmp_path, monkeypatch)
    legacy_root = tmp_path / "notebook_data/podcasts/videos"
    legacy_file = legacy_root / "legacy/assets/scene.png"
    legacy_file.parent.mkdir(parents=True)
    legacy_file.write_bytes(b"image")
    monkeypatch.setattr(
        video_paths,
        "_existing_legacy_video_roots",
        lambda: (legacy_root.resolve(),),
    )

    assert resolve_contained_video_path(str(legacy_file)) == legacy_file.resolve()


@pytest.mark.asyncio
async def test_asset_file_endpoint_rejects_registered_path_outside_video_root(
    tmp_path, monkeypatch
):
    _video_root(tmp_path, monkeypatch)
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"secret")
    video = SimpleNamespace(assets=[{"id": "asset-1", "path": str(outside)}])

    async def fake_get(_video_id):
        return video

    monkeypatch.setattr("api.routers.podcasts.VideoService.get", fake_get)

    with pytest.raises(HTTPException) as exc_info:
        await stream_episode_video_asset_file("episode_video:test", "asset-1")

    assert exc_info.value.status_code == 403


def test_episode_base_dir_resolves_v113_relative_audio_path(tmp_path, monkeypatch):
    podcasts_root = tmp_path / "podcasts"
    monkeypatch.setattr(audio_paths, "PODCASTS_FOLDER", str(podcasts_root))
    audio_path = podcasts_root / "episodes/episode-1/audio/source.mp3"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"audio")
    episode = _episode_with_transcript()
    episode.audio_file = "episodes/episode-1/audio/source.mp3"

    assert _episode_base_dir(episode) == podcasts_root / "episodes/episode-1"


@pytest.mark.asyncio
async def test_openai_image_generation_revalidates_credential_base_url(tmp_path):
    credential = SimpleNamespace(
        to_esperanto_config=lambda: {
            "api_key": "test-key",
            "base_url": "http://169.254.169.254/v1",
        }
    )

    async def get_credential_obj():
        return credential

    model = cast(
        Model,
        SimpleNamespace(
            credential="credential:test",
            get_credential_obj=get_credential_obj,
            name="gpt-image-1",
        ),
    )

    with pytest.raises(ValueError, match="Link-local"):
        await generate_openai_image(
            prompt="test",
            output_path=tmp_path / "image.png",
            model=model,
            canvas=DEFAULT_CANVAS,
        )


@pytest.mark.asyncio
async def test_image_model_connection_test_accepts_provider_env_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    model = SimpleNamespace(
        type="image_generation",
        provider="openai",
        credential=None,
    )

    success, message = await _test_individual_model(model)

    assert success is True
    assert message == "Image generation credential is configured"


@pytest.mark.asyncio
async def test_completed_job_status_links_generated_video(tmp_path, monkeypatch):
    video_path = _video_root(tmp_path, monkeypatch) / "video-1/renders/episode.mp4"
    video_path.parent.mkdir(parents=True)
    video_path.write_bytes(b"video")
    status = SimpleNamespace(
        status="completed",
        result={"video_id": "episode_video:test"},
        error_message=None,
    )
    video = SimpleNamespace(id="episode_video:test", video_file=str(video_path))

    async def fake_get_status(job_id):
        assert job_id == "command:test"
        return status

    async def fake_get_video(video_id):
        assert video_id == "episode_video:test"
        return video

    monkeypatch.setattr("api.video_service.get_command_status", fake_get_status)
    monkeypatch.setattr("api.video_service.get_episode_video", fake_get_video)

    response = await VideoService.get_job_status("command:test")

    assert response["episode_video_id"] == "episode_video:test"
    assert response["video_url"] == ("/api/podcasts/videos/episode_video%3Atest/file")
