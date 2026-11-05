"""Tests for the read-a-script podcast path (API, retry and background command)."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from commands.podcast_commands import (
    SCRIPT_EPISODE_PROFILE,
    ScriptPodcastInput,
    read_script_podcast_command,
)
from open_notebook.podcasts.models import PodcastEpisode, SpeakerProfile


def make_profile(**overrides):
    data = dict(
        id="speaker_profile:sp1",
        name="velvet_noir",
        voice_model="model:tts1",
        speakers=[
            {
                "name": "Velvet Noir",
                "voice_id": "af_bella",
                "backstory": "b",
                "personality": "p",
            },
            {
                "name": "Max",
                "voice_id": "am_adam",
                "backstory": "b",
                "personality": "p",
            },
        ],
    )
    data.update(overrides)
    return SpeakerProfile(**data)


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


def _post(client, profile, body):
    with (
        patch(
            "api.podcast_service.SpeakerProfile.resolve",
            new=AsyncMock(return_value=profile),
        ),
        patch(
            "api.podcast_service.submit_command", return_value="command:job1"
        ) as submit,
    ):
        resp = client.post("/api/podcasts/read-script", json=body)
    return resp, submit


class TestReadScriptApi:
    def test_submits_job_with_resolved_profile_id(self, client):
        body = {
            "speaker_profile": "velvet_noir",
            "episode_name": "Ep 1",
            "script": "Max: Hi there.",
        }
        resp, submit = _post(client, make_profile(), body)
        assert resp.status_code == 200
        assert resp.json()["job_id"] == "command:job1"
        app_name, command, args = submit.call_args.args
        assert command == "read_script_podcast"
        assert args == {
            "speaker_profile": "speaker_profile:sp1",
            "episode_name": "Ep 1",
            "script": "Max: Hi there.",
            "notebook_id": None,
        }

    def test_empty_script_is_400_and_submits_nothing(self, client):
        body = {"speaker_profile": "x", "episode_name": "E", "script": " \n# \n"}
        resp, submit = _post(client, make_profile(), body)
        assert resp.status_code == 400
        submit.assert_not_called()

    def test_unknown_profile_is_404(self, client):
        body = {"speaker_profile": "nope", "episode_name": "E", "script": "Hi."}
        resp, submit = _post(client, None, body)
        assert resp.status_code == 404
        assert "not found" in resp.text
        submit.assert_not_called()

    def test_profile_without_voice_model_is_400(self, client):
        body = {"speaker_profile": "x", "episode_name": "E", "script": "Hi."}
        resp, _ = _post(client, make_profile(voice_model=None), body)
        assert resp.status_code == 400


def test_retry_resubmits_a_script_episode_as_a_script(client):
    ep = PodcastEpisode(
        id="episode:e1",
        name="Ep 1",
        episode_profile=dict(SCRIPT_EPISODE_PROFILE),
        speaker_profile={"name": "velvet_noir"},
        briefing="b",
        content="Max: Hi.",
        command="command:old",
        notebook="notebook:n1",
    )
    with (
        patch(
            "api.routers.podcasts.PodcastService.get_episode",
            new=AsyncMock(return_value=ep),
        ),
        patch.object(
            PodcastEpisode,
            "get_job_detail",
            new=AsyncMock(return_value={"status": "failed", "error_message": "x"}),
        ),
        patch.object(PodcastEpisode, "delete", new=AsyncMock()) as delete,
        patch(
            "api.routers.podcasts.PodcastService.submit_script_job",
            new=AsyncMock(return_value="command:new"),
        ) as submit,
    ):
        resp = client.post("/api/podcasts/episodes/episode:e1/retry")
    assert resp.status_code == 200
    delete.assert_awaited_once()
    submit.assert_awaited_once_with(
        speaker_profile_name="velvet_noir",
        episode_name="Ep 1",
        script="Max: Hi.",
        notebook_id="notebook:n1",
    )


@pytest.mark.asyncio
async def test_command_reads_each_clip_with_its_speakers_voice(tmp_path):
    profile = make_profile()
    clips = []

    async def fake_clip(info):
        clips.append(
            (info["voices"][info["dialogue"].speaker], info["dialogue"].dialogue)
        )
        return tmp_path / f"{info['index']}.mp3"

    async def fake_combine(clips_dir, filename, audio_dir, gap_ms):
        return {"combined_audio_path": str(tmp_path / "episodes" / "x" / filename)}

    saved_paths = []

    async def fake_save(self):
        self.id = self.id or "episode:new"
        saved_paths.append(self.audio_file)

    with (
        patch.object(SpeakerProfile, "resolve", new=AsyncMock(return_value=profile)),
        patch.object(
            SpeakerProfile,
            "resolve_tts_config",
            new=AsyncMock(return_value=("openai_compatible", "kokoro", {})),
        ),
        patch.object(PodcastEpisode, "save", new=fake_save),
        patch(
            "commands.podcast_commands.write_episode_progress", new=AsyncMock()
        ) as prog,
        patch("commands.podcast_commands.PODCASTS_FOLDER", str(tmp_path)),
        patch("podcast_creator.nodes.generate_single_audio_clip", new=fake_clip),
        patch("podcast_creator.nodes.combine_audio_files", new=fake_combine),
        patch(
            "commands.podcast_commands.to_relative_audio_path",
            side_effect=lambda p: "episodes/x/final.mp3",
        ),
        patch(
            "commands.podcast_commands.build_episode_output_dir",
            return_value=("x", tmp_path / "episodes" / "x"),
        ),
    ):
        result = await read_script_podcast_command(
            ScriptPodcastInput(
                speaker_profile="speaker_profile:sp1",
                episode_name="Ep",
                script="Intro line.\n\nMax: Hello.",
            )
        )

    assert result.success
    assert clips == [("af_bella", "Intro line."), ("am_adam", "Hello.")]
    assert result.transcript == {
        "transcript": [
            {"speaker": "Velvet Noir", "dialogue": "Intro line."},
            {"speaker": "Max", "dialogue": "Hello."},
        ]
    }
    assert saved_paths[-1] == "episodes/x/final.mp3"
    assert prog.await_args_list[-1].args[1] == 100
