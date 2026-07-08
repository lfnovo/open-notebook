from dataclasses import dataclass, field
from typing import Dict, List

DEFAULT_VIDEO_STYLE_PRESET = "notebooklm_whiteboard_explainer"


@dataclass(frozen=True)
class VideoStylePreset:
    """Codex-editable preset for storyboard and generated slide prompts."""

    name: str
    description: str
    storyboard_template: str
    image_prompt_template: str
    visual_style: str
    storyboard_guidance: str
    image_prompt_guidance: str
    default_scene_density: str = "balanced"
    target_scene_seconds: Dict[str, float] = field(
        default_factory=lambda: {"dense": 12.0, "balanced": 18.0, "sparse": 24.0}
    )


VIDEO_STYLE_PRESETS: Dict[str, VideoStylePreset] = {
    DEFAULT_VIDEO_STYLE_PRESET: VideoStylePreset(
        name=DEFAULT_VIDEO_STYLE_PRESET,
        description=(
            "NotebookLM-like whiteboard explainer slides: concept diagrams, "
            "hand-drawn metaphors, Russian text inside each generated slide."
        ),
        storyboard_template="storyboard.jinja",
        image_prompt_template="image_prompt_whiteboard.jinja",
        visual_style=(
            "16:9 whiteboard explainer slide, white paper background with a very "
            "subtle grid, black hand-drawn line art, clean educational composition, "
            "limited accents in soft pink, yellow, teal, and green."
        ),
        storyboard_guidance=(
            "Turn the narration into frequent visual teaching beats. Prefer diagrams, "
            "mini-cases, formulas, comparisons, questions, and metaphors over generic "
            "office scenes. Each beat must help the viewer understand one concept. "
            "Choose visible text as compact labels or takeaways, not as copied narration."
        ),
        image_prompt_guidance=(
            "Generate the whole slide as one final image. All Russian text must be "
            "inside the image. Use only short complete labels, never ellipses, cropped "
            "phrases, paragraph fragments, or voiceover sentences. Do not reserve space "
            "for external overlays, captions, logos, watermarks, or UI chrome."
        ),
    ),
    "corporate_training_clean_ru": VideoStylePreset(
        name="corporate_training_clean_ru",
        description=(
            "Clean corporate training explainer slides with restrained diagrammatic "
            "visuals and Russian text embedded in the generated slide."
        ),
        storyboard_template="storyboard.jinja",
        image_prompt_template="image_prompt_whiteboard.jinja",
        visual_style=(
            "16:9 clean corporate training slide, structured layout, light neutral "
            "background, simple vector-like diagrams, restrained accent colors."
        ),
        storyboard_guidance=(
            "Create practical management teaching beats. Use structured diagrams and "
            "short Russian text instead of stock-photo backgrounds. Choose visible text "
            "as labels or takeaways, not as copied narration."
        ),
        image_prompt_guidance=(
            "Generate a complete slide image with all visible text baked in. Keep text "
            "short, legible, complete, and directly tied to the concept. Never use "
            "ellipses, cropped phrases, or long voiceover sentences."
        ),
        target_scene_seconds={"dense": 14.0, "balanced": 22.0, "sparse": 30.0},
    ),
}


def get_video_style_preset(name: str | None) -> VideoStylePreset:
    preset_name = name or DEFAULT_VIDEO_STYLE_PRESET
    try:
        return VIDEO_STYLE_PRESETS[preset_name]
    except KeyError as exc:
        available = ", ".join(sorted(VIDEO_STYLE_PRESETS))
        raise ValueError(
            f"Unknown video style preset '{preset_name}'. Available presets: {available}"
        ) from exc


def list_video_style_presets() -> List[dict]:
    return [
        {
            "name": preset.name,
            "description": preset.description,
            "default_scene_density": preset.default_scene_density,
            "target_scene_seconds": preset.target_scene_seconds,
        }
        for preset in VIDEO_STYLE_PRESETS.values()
    ]
