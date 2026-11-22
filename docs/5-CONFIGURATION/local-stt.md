# Local Speech-to-Text

Transcribe audio and video sources (and YouTube videos without subtitles) on your own hardware.

Setup is shared with local text-to-speech: run [Speaches](https://github.com/speaches-ai/speaches), add it as an **OpenAI Compatible** configuration in Manage → Models, add a model with **Model Type** **STT**, and choose it as the **Speech-to-Text Model** under Default Model Assignments. Follow [Local Speech with Speaches](local-tts.md) for those steps; this page covers what is specific to transcription.

---

## Choosing a Whisper model

Speaches transcribes with [faster-whisper](https://github.com/SYSTRAN/faster-whisper). Download the model you want before using it:

```bash
docker compose exec speaches uv tool run speaches-cli model download Systran/faster-whisper-small
```

| Model id | Notes |
|----------|-------|
| `Systran/faster-whisper-tiny`, `Systran/faster-whisper-base` | Fastest, least accurate |
| `Systran/faster-whisper-small` | A reasonable default on CPU |
| `Systran/faster-whisper-medium` | More accurate, much slower on CPU |
| `Systran/faster-whisper-large-v3` | Most accurate; use a GPU |

`speaches-cli registry ls --task automatic-speech-recognition` lists everything Speaches can download. Register the model in Open Notebook under the exact same id.

Test it:

```bash
curl http://localhost:8969/v1/audio/transcriptions \
  -F "file=@test.mp3" -F "model=Systran/faster-whisper-small"
```

---

## Long recordings

Before transcription, Open Notebook (through content-core) splits long audio and video into 10-minute segments and transcribes up to 3 at a time. Cloud APIs need this because of their upload limits; a local server usually doesn't. These variables go in the `open_notebook` environment (apply with `docker compose up -d`):

| Variable | Default | Use |
|----------|---------|-----|
| `CCORE_AUDIO_SEGMENT_MINUTES` | `10` | `0` sends each file whole, so Whisper sees the full context |
| `CCORE_AUDIO_CONCURRENCY` | `3` | Segments sent in parallel (1–10). Use `1` for a single CPU or GPU server |
| `CCORE_STT_TIMEOUT` | `3600` | Seconds allowed per transcription request. Raise it if a whole file on CPU takes longer than an hour |

See the [Environment Reference](environment-reference.md#content-extraction).

---

## When transcription fails

The source shows **Failed**. The reason is in the worker log:

```bash
docker compose logs open_notebook | grep -i "content-core extraction failed"
```

Common causes:

- No **Speech-to-Text Model** assigned, or the Speaches configuration's Base URL is wrong.
- The model id isn't downloaded in Speaches. Download it (see above).
- The request timed out on a long file. Raise `CCORE_STT_TIMEOUT` or keep segmenting on.

Depending on the error, the failure reason reads "Content extraction is not configured correctly. Check the content processing engine and speech-to-text settings; the worker log has the details." or "The content extraction service failed."

More failure messages: [Processing Issues → Failed sources](../6-TROUBLESHOOTING/processing-issues.md#failed-sources).

---

## Related

- [Local Speech with Speaches](local-tts.md) — shared setup, text-to-speech
- [OpenAI-Compatible Providers](openai-compatible.md)
- [Adding Sources](../3-USER-GUIDE/adding-sources.md)
