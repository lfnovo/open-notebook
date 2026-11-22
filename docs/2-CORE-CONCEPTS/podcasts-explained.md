# Podcasts Explained - Research as Audio Dialogue

Open Notebook can turn sources and notes into a podcast episode: a scripted conversation (or monologue) between one to four speakers, voiced with text-to-speech. This page explains how generation works and what the settings mean. For the step-by-step, see [Creating Podcasts](../3-USER-GUIDE/creating-podcasts.md).

---

## The Building Blocks

**Speaker profile**: who talks and how they sound.
- A **voice model** (a text-to-speech model, selected in the speaker profile). Without one, the **Default Text-to-Speech Model** from Manage → Models is used; generation fails only if neither is set.
- One to four **speakers**, each with a name, a **Voice ID** (a voice name of that TTS model), a backstory and a personality.
- Optionally, a different voice model per speaker (*Per-speaker TTS override*), so speakers can come from different TTS providers.

**Episode profile**: how the episode is written.
- The **speaker profile** to use.
- An **outline model** and a **transcript model** (language models).
- The number of **segments** (3 to 20).
- A **default briefing**: free-text instructions for structure, tone and audience.
- An optional **language** (a locale such as `en-US` or `pt-BR`) for the outline and transcript.
- Optional **max output tokens** per generation step (default 8192).

**Episode**: one generation run. You pick the content, an episode profile, a name and optional additional instructions.

Open Notebook ships with three episode profiles (`tech_discussion`, `solo_expert`, `business_analysis`) and three speaker profiles (`tech_experts`, `solo_expert`, `business_panel`). On a new install **they have no models assigned**, so they show a *Setup required* badge until you edit them and pick an outline model, a transcript model and a voice model. The speaker profiles also work without a voice model once a Default Text-to-Speech Model is set in Manage → Models (the badge still shows). (Installations upgraded from older versions may already have models on them, if matching models were registered.) Their Voice IDs are OpenAI voice names (`nova`, `alloy`, ...); change them if you use another TTS provider.

---

## How Generation Works

```
Selected content (sources at Summary or Full content, notes)
        │
        ▼
1. OUTLINE      outline model + briefing → a plan with N segments
        │
        ▼
2. TRANSCRIPT   transcript model writes the dialogue, segment by segment,
        │       using the speakers' names, backstories and personalities
        ▼
3. AUDIO        each line is voiced with its speaker's voice model and Voice ID,
                then the clips are joined into one audio file
```

- **Briefing**: the episode profile's default briefing, plus the episode's *Additional instructions* appended at the end.
- **Language**: when set on the episode profile, the outline and transcript are written in that language. The TTS voice must support it too.
- **Content**: for each source you choose *Summary* (its title and [insights](notebooks-sources-notes.md#insights)) or *Full content* (title, insights and full text). Notes are included in full. A source with no insights contributes almost nothing at *Summary*.
- **Background job**: generation runs in the worker, so you can close the browser. If the worker isn't running, episodes stay pending.

---

## Privacy: What Each Model Sees

| Step | Model | What it receives |
|------|-------|------------------|
| Outline | Outline model | All selected content, the briefing, speaker descriptions |
| Transcript | Transcript model | The outline, the selected content, the briefing, speaker descriptions |
| Audio | Voice model(s) | The transcript text, line by line |

Local text-to-speech alone does not keep your content local: the outline and transcript models see the full selected content. For a fully local podcast, use local language models **and** a local TTS server (see [Local TTS](../5-CONFIGURATION/local-tts.md)).

---

## Cost

An episode costs the outline and transcript language-model calls (which include all selected content) plus text-to-speech for the whole script. More content, more segments and longer briefings all increase it. Check your providers' current pricing; local models cost nothing per call.

---

## When Things Go Wrong: Failures & Retry

When generation fails, the episode moves to **Failed Episodes** and its card shows the error message. For common failures the message ends with a **NOTE** explaining the likely cause. Failed jobs are not retried automatically.

To try again, click **Retry** on the failed episode. The failed episode is deleted and a new job is submitted with the same settings.

| Error | What to do |
|-------|-----------|
| `... has no outline model configured` / `no transcript model configured` | Edit the episode profile and pick the model. The seeded profiles ship without models. |
| `... has no voice model configured and no default Text-to-Speech model is set` | Pick a voice model in the speaker profile, or set a **Default Text-to-Speech Model** in Manage → Models. |
| `Invalid speaker name` | The transcript model used a name that isn't in the speaker profile. Retrying usually works. |
| `Voice name ... not supported` or `Requested entity was not found` (Google) | The Voice ID doesn't exist for that voice model. Use a voice name your TTS model provides. |
| `Invalid json output` / `Expecting value` | The model's output was cut off or empty. Lower **Max output tokens** to the model's real limit, use fewer segments, or avoid models that put all output in thinking blocks. |
| Invalid API key, model not found, rate limit | Check the credential and models under **Manage → Models**, then retry. |

Unconfigured profiles you are *not* using don't block generation; they are skipped.
