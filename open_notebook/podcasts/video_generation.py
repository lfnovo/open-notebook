import asyncio
import base64
import json
import os
import re
import shutil
import subprocess
import textwrap
import uuid
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import BaseMessage
from loguru import logger
from PIL import Image, ImageDraw, ImageFont, ImageOps

from open_notebook.ai.models import DefaultModels, Model
from open_notebook.ai.provision import provision_langchain_model
from open_notebook.config import DATA_FOLDER
from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.podcasts.audio_paths import resolve_contained_audio_path
from open_notebook.podcasts.models import EpisodeVideo, PodcastEpisode
from open_notebook.podcasts.video_paths import resolve_contained_video_path
from open_notebook.podcasts.video_presets import (
    DEFAULT_VIDEO_STYLE_PRESET,
    VideoStylePreset,
    get_video_style_preset,
)
from open_notebook.utils.text_utils import clean_thinking_content, extract_text_content
from open_notebook.utils.url_validation import validate_url

DEFAULT_CANVAS = {"width": 1920, "height": 1080, "fps": 30}
VIDEO_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts" / "podcast" / "video"
GOOGLE_IMAGE_FALLBACK_MODELS = [
    "gemini-2.5-flash-image",
    "gemini-3.1-flash-lite-image",
    "gemini-3.1-flash-image",
    "gemini-3-pro-image",
]
OPENAI_IMAGE_FALLBACK_MODELS = [
    "gpt-image-2",
    "gpt-image-1",
]
VISIBLE_TEXT_MAX_CHARS = 34
VISIBLE_TEXT_MAX_WORDS = 5


def _template_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(VIDEO_PROMPTS_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _render_video_prompt(template_name: str, **context: Any) -> str:
    return _template_env().get_template(template_name).render(**context).strip()


def build_video_output_dir(data_folder: str = DATA_FOLDER) -> tuple[str, Path]:
    video_dir_name = str(uuid.uuid4())
    output_dir = Path(data_folder) / "podcasts" / "videos" / video_dir_name
    return video_dir_name, output_dir


def _episode_base_dir(episode: PodcastEpisode) -> Optional[Path]:
    if not episode.audio_file:
        return None
    audio_path = resolve_contained_audio_path(episode.audio_file)
    if audio_path is None:
        return None
    if audio_path.parent.name == "audio":
        return audio_path.parent.parent
    return audio_path.parent


def _extract_transcript_entries(episode: PodcastEpisode) -> List[Dict[str, Any]]:
    transcript = episode.transcript or {}
    entries: Any = transcript
    if isinstance(transcript, dict):
        entries = transcript.get("transcript") or transcript.get("dialogue") or []
    if not isinstance(entries, list):
        return []

    normalized = []
    for idx, entry in enumerate(entries):
        if isinstance(entry, dict):
            text = entry.get("dialogue") or entry.get("text") or entry.get("content") or ""
            speaker = entry.get("speaker") or "Narrator"
        else:
            text = str(entry)
            speaker = "Narrator"
        text = " ".join(str(text).split())
        if text:
            normalized.append(
                {
                    "clip_id": f"{idx:04d}",
                    "speaker": str(speaker),
                    "text": text,
                }
            )
    return normalized


def _probe_duration(path: Path) -> Optional[float]:
    if not path.exists():
        return None
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"Could not probe duration for {path}: {e}")
        return None


def _entry_durations(episode: PodcastEpisode, entries: List[Dict[str, Any]]) -> List[float]:
    base_dir = _episode_base_dir(episode)
    clips_dir = base_dir / "clips" if base_dir else None
    durations = []
    if clips_dir and clips_dir.exists():
        for entry in entries:
            clip_path = clips_dir / f"{entry['clip_id']}.mp3"
            durations.append(_probe_duration(clip_path) or 0.0)

    if durations and any(duration > 0 for duration in durations):
        return durations

    audio_path = resolve_contained_audio_path(episode.audio_file)
    audio_duration = _probe_duration(audio_path) if audio_path is not None else None
    if not audio_duration or not entries:
        return [30.0 for _ in entries]
    per_entry = audio_duration / len(entries)
    return [per_entry for _ in entries]


def _target_scene_duration(scene_density: str, preset: VideoStylePreset) -> float:
    density = scene_density or preset.default_scene_density
    return preset.target_scene_seconds.get(
        density,
        preset.target_scene_seconds.get(preset.default_scene_density, 18.0),
    )


def _initial_scene_groups(
    entries: List[Dict[str, Any]],
    durations: List[float],
    scene_density: str,
    preset: VideoStylePreset,
) -> List[Dict[str, Any]]:
    target = _target_scene_duration(scene_density, preset)
    scenes = []
    current_entries: List[Dict[str, Any]] = []
    current_duration = 0.0
    start = 0.0
    cursor = 0.0

    for idx, (entry, duration) in enumerate(zip(entries, durations)):
        if not current_entries:
            start = cursor
        current_entries.append(entry)
        current_duration += duration
        cursor += duration
        next_duration = durations[idx + 1] if idx + 1 < len(durations) else 0
        if current_duration >= target or (
            current_duration >= target * 0.7 and next_duration > target * 0.55
        ):
            scenes.append(
                {
                    "from": round(start, 3),
                    "duration": round(current_duration, 3),
                    "narration_clip_ids": [item["clip_id"] for item in current_entries],
                    "source_text": " ".join(item["text"] for item in current_entries),
                }
            )
            current_entries = []
            current_duration = 0.0

    if current_entries:
        scenes.append(
            {
                "from": round(start, 3),
                "duration": round(current_duration, 3),
                "narration_clip_ids": [item["clip_id"] for item in current_entries],
                "source_text": " ".join(item["text"] for item in current_entries),
            }
        )
    return scenes


def _split_sentences(text: str) -> List[str]:
    normalized = " ".join(text.split())
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?;])\s+", normalized)
        if sentence.strip()
    ]


def _shorten(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip(" ,.;:-") + "…"


def _shorten_without_ellipsis(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip(" ,.;:-")


def _default_exact_text_for_slide_type(slide_type: str) -> List[str]:
    if slide_type == "formula":
        return ["Цифра", "Причина", "Зона контроля", "Действие"]
    if slide_type == "comparison":
        return ["Старая позиция", "Новая позиция"]
    if slide_type == "question":
        return ["Ключевой вопрос"]
    if slide_type == "mini_case":
        return ["Помощь или подмена?"]
    if slide_type == "definition":
        return ["Простое определение"]
    if slide_type == "quote":
        return ["Главная мысль"]
    if slide_type == "metaphor":
        return ["Не спасать", "Развивать навык"]
    return ["Следующее действие"]


def _normalize_visible_text_phrase(value: Any) -> str:
    text = " ".join(str(value).split())
    text = text.replace("…", "").replace("...", "")
    text = text.strip(" \t\r\n-–—:;,.!\"'«»")
    if not text:
        return ""

    words = text.split()
    if len(text) > VISIBLE_TEXT_MAX_CHARS or len(words) > VISIBLE_TEXT_MAX_WORDS:
        return ""

    return text


def _guess_slide_type(index: int, source_text: str) -> str:
    lowered = source_text.lower()
    if "->" in source_text or "формул" in lowered or "этап" in lowered or "шаг" in lowered:
        return "formula"
    if "стар" in lowered and "нов" in lowered:
        return "comparison"
    if "пример" in lowered or "ситуац" in lowered or "клиент" in lowered:
        return "mini_case"
    if "почему" in lowered or "что " in lowered or "как " in lowered:
        return "question"
    if "роль" in lowered:
        return "metaphor"
    return ["process", "metaphor", "comparison", "question"][index % 4]


def _deterministic_exact_text(source_text: str, slide_type: str, index: int) -> List[str]:
    return _default_exact_text_for_slide_type(slide_type)


def _simple_scene_from_group(index: int, group: Dict[str, Any]) -> Dict[str, Any]:
    source_text = group["source_text"]
    slide_type = _guess_slide_type(index, source_text)
    exact_text = _deterministic_exact_text(source_text, slide_type, index)
    title = exact_text[0] if exact_text else f"Сцена {index + 1}"

    return {
        "id": f"scene-{index + 1:03d}",
        "from": group["from"],
        "duration": group["duration"],
        "narration_clip_ids": group["narration_clip_ids"],
        "title": title,
        "slide_type": slide_type,
        "narration_summary": _shorten(source_text, 180),
        "learning_intent": (
            "Помочь зрителю увидеть управленческий смысл, а не просто услышать тезис."
        ),
        "visual_concept": (
            "Показать управленческий выбор или схему, которая объясняет этот фрагмент."
        ),
        "text_strategy": (
            "Использовать короткие подписи как навигацию по смыслу, не дублируя озвучку."
        ),
        "exact_text": exact_text,
        "visual_instruction": (
            "Покажи понятную обучающую схему или метафору, связанную с этим фрагментом: "
            f"{_shorten_without_ellipsis(source_text, 360)}"
        ),
        "asset_id": f"asset-scene-{index + 1:03d}-v1",
        "effects": [],
    }


async def _call_storyboard_llm(
    scenes: List[Dict[str, Any]],
    episode: PodcastEpisode,
    briefing: str,
    language_model_id: Optional[str],
    preset: VideoStylePreset,
) -> Optional[List[Dict[str, Any]]]:
    prompt_scenes = [
        {
            "id": f"scene-{idx + 1:03d}",
            "duration": scene["duration"],
            "clip_ids": scene["narration_clip_ids"],
            "text": scene["source_text"][:1400],
        }
        for idx, scene in enumerate(scenes)
    ]
    prompt = _render_video_prompt(
        preset.storyboard_template,
        preset=preset,
        briefing=briefing,
        episode_name=episode.name,
        scenes_json=json.dumps(prompt_scenes, ensure_ascii=False, indent=2),
    )
    try:
        model = await provision_langchain_model(
            prompt,
            language_model_id,
            "chat",
            max_tokens=5000,
            structured=dict(type="json"),
        )
        response = await model.ainvoke(prompt)
        content = response.content if isinstance(response, BaseMessage) else response
        text = clean_thinking_content(extract_text_content(content))
        if text.strip().startswith("```"):
            text = text.strip().strip("`")
            if text.startswith("json"):
                text = text[4:]
        parsed = json.loads(text)
        llm_scenes = parsed.get("scenes")
        if isinstance(llm_scenes, list) and len(llm_scenes) == len(scenes):
            return llm_scenes
    except Exception as e:
        logger.warning(f"Storyboard LLM failed, using deterministic storyboard: {e}")
    return None


def _normalize_storyboard_text_items(
    value: Any, fallback: List[str], slide_type: str
) -> List[str]:
    items = value if isinstance(value, list) else fallback
    received_visible_text = isinstance(value, list) and bool(value)
    normalized = []
    for item in items:
        text = _normalize_visible_text_phrase(item)
        if text and text not in normalized:
            normalized.append(text)

    max_items = 4 if slide_type == "formula" else 2
    if normalized:
        return normalized[:max_items]

    if received_visible_text:
        return _default_exact_text_for_slide_type(slide_type)[:max_items]

    fallback_items = [
        text
        for text in (_normalize_visible_text_phrase(item) for item in fallback)
        if text
    ]
    if fallback_items:
        return fallback_items[:max_items]
    return _default_exact_text_for_slide_type(slide_type)[:max_items]


def _build_image_prompt(
    item: Dict[str, Any],
    preset: VideoStylePreset,
) -> str:
    prompt = _render_video_prompt(
        preset.image_prompt_template,
        preset=preset,
        item=item,
    )
    return prompt


def _apply_image_prompts(storyboard: Dict[str, Any], preset: VideoStylePreset) -> None:
    for item in storyboard.get("items", []):
        image_prompt = _build_image_prompt(item, preset)
        item["image_prompt"] = image_prompt
        item["visual_prompt"] = image_prompt
        item["prompt_preset"] = preset.name


PROMPT_SOURCE_FIELDS = {
    "slide_type",
    "narration_summary",
    "learning_intent",
    "visual_concept",
    "text_strategy",
    "exact_text",
    "visual_instruction",
}


async def build_storyboard(
    episode: PodcastEpisode,
    briefing: str,
    language_model_id: Optional[str],
    scene_density: str,
    canvas: Dict[str, Any],
    style_preset: str = DEFAULT_VIDEO_STYLE_PRESET,
) -> Dict[str, Any]:
    preset = get_video_style_preset(style_preset)
    entries = _extract_transcript_entries(episode)
    if not entries:
        raise ValueError("Episode transcript is empty; cannot build storyboard")
    durations = _entry_durations(episode, entries)
    groups = _initial_scene_groups(entries, durations, scene_density, preset)
    base_scenes = [_simple_scene_from_group(idx, group) for idx, group in enumerate(groups)]

    llm_scenes = await _call_storyboard_llm(
        groups, episode, briefing, language_model_id, preset
    )
    if llm_scenes:
        for scene, llm_scene in zip(base_scenes, llm_scenes):
            scene["title"] = str(llm_scene.get("title") or scene["title"])[:120]
            scene["slide_type"] = str(
                llm_scene.get("slide_type") or scene["slide_type"]
            )[:40]
            scene["narration_summary"] = _shorten(
                llm_scene.get("narration_summary") or scene["narration_summary"],
                220,
            )
            scene["learning_intent"] = _shorten(
                llm_scene.get("learning_intent") or scene["learning_intent"],
                220,
            )
            scene["visual_concept"] = _shorten(
                llm_scene.get("visual_concept") or scene["visual_concept"],
                260,
            )
            scene["text_strategy"] = _shorten(
                llm_scene.get("text_strategy") or scene["text_strategy"],
                260,
            )
            scene["exact_text"] = _normalize_storyboard_text_items(
                llm_scene.get("exact_text"), scene["exact_text"], scene["slide_type"]
            )
            scene["visual_instruction"] = _shorten(
                llm_scene.get("visual_instruction") or scene["visual_instruction"],
                520,
            )

    total_duration = sum(scene["duration"] for scene in base_scenes)
    storyboard = {
        "version": 1,
        "audio_episode_id": str(episode.id),
        "canvas": canvas,
        "duration": round(total_duration, 3),
        "style_preset": preset.name,
        "style_description": preset.description,
        "items": base_scenes,
    }
    _apply_image_prompts(storyboard, preset)
    return storyboard


async def _resolve_model(model_id: Optional[str], default_attr: str) -> Model:
    if not model_id:
        defaults = await DefaultModels.get_instance()
        model_id = getattr(defaults, default_attr)
    if not model_id:
        raise ValueError(f"No model configured for {default_attr}")
    return await Model.get(str(model_id))


def _write_fallback_image(path: Path, prompt: str, size: tuple[int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = size
    img = Image.new("RGB", size, (237, 241, 245))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        shade = int(237 - y / height * 24)
        draw.line([(0, y), (width, y)], fill=(shade, shade + 4, min(255, shade + 11)))
    draw.rectangle((0, height - 240, width, height), fill=(32, 58, 70))
    draw.ellipse((width - 520, 120, width - 80, 560), fill=(92, 157, 146))
    draw.ellipse((width - 680, 260, width - 280, 660), fill=(226, 184, 90))
    font = _load_font(44)
    text = "\n".join(textwrap.wrap(prompt[:280], width=48))
    draw.text((80, height - 205), text, fill=(255, 255, 255), font=font)
    img.save(path)


def _extract_inline_image(response: Any) -> Optional[bytes]:
    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", []) or []:
            inline_data = getattr(part, "inline_data", None)
            data = getattr(inline_data, "data", None) if inline_data else None
            if data:
                if isinstance(data, bytes):
                    return data
                if isinstance(data, str):
                    return base64.b64decode(data)
    for image in getattr(response, "generated_images", []) or []:
        data = getattr(getattr(image, "image", None), "image_bytes", None)
        if data:
            return data
    return None


async def generate_google_image(
    prompt: str,
    output_path: Path,
    model: Model,
    canvas: Dict[str, Any],
) -> Dict[str, Any]:
    from google import genai
    from google.genai import types

    credential = await model.get_credential_obj() if model.credential else None
    config = credential.to_esperanto_config() if credential else {}
    api_key = (
        config.get("api_key")
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
    )
    if not api_key:
        raise ValueError("Google image generation requires an API key")

    model_candidates = [model.name]
    for candidate in GOOGLE_IMAGE_FALLBACK_MODELS:
        if candidate not in model_candidates:
            model_candidates.append(candidate)

    def _generate() -> tuple[bytes, str]:
        client = genai.Client(api_key=api_key)
        last_error: Optional[Exception] = None
        for model_name in model_candidates:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["TEXT", "IMAGE"],
                        image_config=types.ImageConfig(
                            aspect_ratio="16:9",
                        ),
                    ),
                )
                image_bytes = _extract_inline_image(response)
                if image_bytes:
                    return image_bytes, model_name
            except Exception as e:
                last_error = e
                logger.warning(f"Google image generation failed with {model_name}: {e}")
        raise RuntimeError(f"No image returned by Google image models: {last_error}")

    image_bytes, actual_model = await asyncio.to_thread(_generate)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_bytes)
    return {
        "provider": "google",
        "requested_model": model.name,
        "actual_model": actual_model,
        "fallback": actual_model != model.name,
    }


def _openai_image_size(
    canvas: Dict[str, Any],
) -> Literal["1536x1024", "1024x1536", "1024x1024"]:
    width = int(canvas.get("width", 1920))
    height = int(canvas.get("height", 1080))
    if width > height:
        return "1536x1024"
    if height > width:
        return "1024x1536"
    return "1024x1024"


def _extract_openai_image(response: Any) -> bytes:
    data = getattr(response, "data", None) or []
    for item in data:
        b64_json = getattr(item, "b64_json", None)
        if b64_json:
            return base64.b64decode(b64_json)
    raise RuntimeError("No image returned by OpenAI image model")


async def generate_openai_image(
    prompt: str,
    output_path: Path,
    model: Model,
    canvas: Dict[str, Any],
) -> Dict[str, Any]:
    from openai import OpenAI

    credential = await model.get_credential_obj() if model.credential else None
    config = credential.to_esperanto_config() if credential else {}
    api_key = config.get("api_key") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI image generation requires an API key")

    base_url = config.get("base_url")
    if base_url:
        await validate_url(base_url, "openai")

    model_candidates = [model.name]
    for candidate in OPENAI_IMAGE_FALLBACK_MODELS:
        if candidate not in model_candidates:
            model_candidates.append(candidate)

    def _generate() -> tuple[bytes, str]:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url or None,
            timeout=120.0,
            max_retries=1,
        )
        last_error: Optional[Exception] = None
        for model_name in model_candidates:
            try:
                response = client.images.generate(
                    model=model_name,
                    prompt=prompt,
                    size=_openai_image_size(canvas),
                )
                return _extract_openai_image(response), model_name
            except Exception as e:
                last_error = e
                logger.warning(f"OpenAI image generation failed with {model_name}: {e}")
        raise RuntimeError(f"No image returned by OpenAI image models: {last_error}")

    image_bytes, actual_model = await asyncio.to_thread(_generate)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_bytes)
    return {
        "provider": "openai",
        "requested_model": model.name,
        "actual_model": actual_model,
        "fallback": actual_model != model.name,
    }


async def generate_scene_assets(
    storyboard: Dict[str, Any],
    output_dir: Path,
    image_model_id: Optional[str],
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    image_model = await _resolve_model(image_model_id, "default_image_generation_model")
    if image_model.type != "image_generation":
        raise ValueError(f"Model {image_model.id} is not an image_generation model")
    if image_model.provider not in {"google", "openai"}:
        raise ValueError("Only google and openai image_generation models are supported in v1")

    canvas = storyboard.get("canvas", DEFAULT_CANVAS)
    size = (int(canvas.get("width", 1920)), int(canvas.get("height", 1080)))
    assets = []
    usage: Dict[str, Any] = {"image_generation": []}

    for item in storyboard.get("items", []):
        asset_id = item["asset_id"]
        asset_path = output_dir / "assets" / f"{asset_id}.png"
        prompt = item.get("image_prompt") or item.get("visual_prompt")
        if not prompt:
            raise ValueError(f"Storyboard item {item.get('id')} has no image prompt")
        try:
            if image_model.provider == "openai":
                provider_usage = await generate_openai_image(
                    prompt=prompt,
                    output_path=asset_path,
                    model=image_model,
                    canvas=canvas,
                )
            else:
                provider_usage = await generate_google_image(
                    prompt=prompt,
                    output_path=asset_path,
                    model=image_model,
                    canvas=canvas,
                )
        except Exception as e:
            logger.warning(f"Falling back to generated placeholder for {asset_id}: {e}")
            _write_fallback_image(asset_path, prompt, size)
            provider_usage = {
                "provider": image_model.provider,
                "requested_model": image_model.name,
                "fallback": True,
                "error": "Image generation failed; fallback placeholder used",
            }

        asset = {
            "id": asset_id,
            "kind": "generated_image",
            "path": str(asset_path),
            "prompt": prompt,
            "model_id": str(image_model.id),
        }
        assets.append(asset)
        usage["image_generation"].append({"asset_id": asset_id, **provider_usage})
        item["asset_path"] = str(asset_path)

    return assets, usage


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def _contain_image(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    image = image.convert("RGB")
    contained = ImageOps.contain(image, size)
    canvas = Image.new("RGB", size, (250, 250, 247))
    left = (size[0] - contained.width) // 2
    top = (size[1] - contained.height) // 2
    canvas.paste(contained, (left, top))
    return canvas


def compose_scene_frame(item: Dict[str, Any], frame_path: Path, canvas: Dict[str, Any]) -> None:
    width = int(canvas.get("width", 1920))
    height = int(canvas.get("height", 1080))
    asset_path = resolve_contained_video_path(item.get("asset_path"))
    if asset_path is None or not asset_path.exists():
        raise ValueError("Storyboard asset path is invalid or missing")
    composed = _contain_image(Image.open(asset_path), (width, height))
    frame_path.parent.mkdir(parents=True, exist_ok=True)
    composed.save(frame_path, quality=95)


def _run_ffmpeg(args: List[str], log_path: Path) -> None:
    result = subprocess.run(args, capture_output=True, text=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write("$ " + " ".join(args) + "\n")
        log_file.write(result.stdout)
        log_file.write(result.stderr)
        log_file.write("\n")
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed with code {result.returncode}: {result.stderr[-1000:]}")


def render_video_from_storyboard(
    episode: PodcastEpisode,
    storyboard: Dict[str, Any],
    output_dir: Path,
) -> str:
    if not episode.audio_file:
        raise ValueError("Episode has no audio file")
    audio_path = resolve_contained_audio_path(episode.audio_file)
    if audio_path is None:
        raise ValueError("Episode audio file path is invalid")
    if not audio_path.exists():
        raise ValueError("Episode audio file does not exist")
    if not shutil.which("ffmpeg"):
        raise ValueError("ffmpeg is not available")

    canvas = storyboard.get("canvas", DEFAULT_CANVAS)
    fps = int(canvas.get("fps", 30))
    log_path = output_dir / "render.log"
    segment_paths = []

    for idx, item in enumerate(storyboard.get("items", [])):
        frame_path = output_dir / "frames" / f"{item['id']}.png"
        segment_path = output_dir / "segments" / f"{idx:04d}-{item['id']}.mp4"
        segment_path.parent.mkdir(parents=True, exist_ok=True)
        compose_scene_frame(item, frame_path, canvas)
        _run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-t",
                str(max(0.2, float(item["duration"]))),
                "-i",
                str(frame_path),
                "-vf",
                f"fps={fps},format=yuv420p",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                str(segment_path),
            ],
            log_path,
        )
        segment_paths.append(segment_path)

    concat_file = output_dir / "segments.txt"
    concat_file.write_text(
        "".join(f"file '{path.resolve().as_posix()}'\n" for path in segment_paths),
        encoding="utf-8",
    )
    final_path = output_dir / "renders" / "final-v1.mp4"
    final_path.parent.mkdir(parents=True, exist_ok=True)
    _run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-i",
            str(audio_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(final_path),
        ],
        log_path,
    )
    return str(final_path)


async def list_episode_videos(episode_id: str) -> List[EpisodeVideo]:
    rows = await repo_query(
        "SELECT * FROM episode_video WHERE episode=$episode ORDER BY created DESC",
        {"episode": ensure_record_id(episode_id)},
    )
    return [EpisodeVideo(**row) for row in rows]


async def get_episode_video(video_id: str) -> EpisodeVideo:
    return await EpisodeVideo.get(video_id)


async def patch_storyboard_item(
    video_id: str,
    item_id: str,
    patch: Dict[str, Any],
) -> EpisodeVideo:
    video = await EpisodeVideo.get(video_id)
    storyboard = dict(video.storyboard or {})
    items = list(storyboard.get("items") or [])
    for item in items:
        if item.get("id") == item_id:
            for key in [
                "title",
                "visual_prompt",
                "image_prompt",
                "slide_type",
                "narration_summary",
                "learning_intent",
                "visual_concept",
                "text_strategy",
                "exact_text",
                "visual_instruction",
                "duration",
            ]:
                if key in patch:
                    item[key] = patch[key]
            if "visual_prompt" in patch and "image_prompt" not in patch:
                item["image_prompt"] = patch["visual_prompt"]
            if "image_prompt" in patch and "visual_prompt" not in patch:
                item["visual_prompt"] = patch["image_prompt"]
            if (
                PROMPT_SOURCE_FIELDS.intersection(patch)
                and "image_prompt" not in patch
                and "visual_prompt" not in patch
            ):
                preset = get_video_style_preset(storyboard.get("style_preset"))
                image_prompt = _build_image_prompt(item, preset)
                item["image_prompt"] = image_prompt
                item["visual_prompt"] = image_prompt
                item["prompt_preset"] = preset.name
            item["asset_id"] = f"asset-{item_id}-v{uuid.uuid4().hex[:8]}"
            item.pop("asset_path", None)
            break
    else:
        raise ValueError(f"Storyboard item not found: {item_id}")
    storyboard["items"] = items
    video.storyboard = storyboard
    video.status = "storyboard_edited"
    await video.save()
    return video
