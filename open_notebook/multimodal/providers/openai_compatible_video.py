import json
from typing import Any, Dict, List, Optional

import httpx

from open_notebook.exceptions import ConfigurationError
from open_notebook.multimodal.base import VideoUnderstandingProvider
from open_notebook.multimodal.types import (
    VideoEntity,
    VideoTimelineSegment,
    VideoUnderstandingInput,
    VideoUnderstandingResult,
)


class OpenAICompatibleVideoProvider(VideoUnderstandingProvider):
    """
    Video understanding adapter for OpenAI-compatible Responses-style APIs.

    The first target is Ark/Doubao's video understanding capability, but the
    adapter is intentionally written against a generic OpenAI-compatible
    request/response shape so it can support other providers later.
    """

    def __init__(
        self,
        *,
        model_name: str,
        base_url: Optional[str],
        api_key: Optional[str] = None,
        timeout: float = 180.0,
    ):
        if not base_url:
            raise ConfigurationError(
                "OpenAI-compatible video understanding requires a base_url"
            )
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    async def analyze(
        self, input_data: VideoUnderstandingInput
    ) -> VideoUnderstandingResult:
        if not input_data.url:
            raise ValueError(
                "Video understanding currently requires a directly accessible video URL"
            )

        payload = self._build_payload(input_data)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/responses",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            body = response.json()

        return self._normalize_response(body, transcript_used=bool(input_data.transcript_markdown))

    async def test_connection(self) -> tuple[bool, str]:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=min(self.timeout, 10.0)) as client:
                response = await client.get(f"{self.base_url}/models", headers=headers)

            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])
                if models:
                    return True, f"Connected. {len(models)} models available."
                return True, "Connected successfully (no models listed)"
            if response.status_code == 401:
                return False, "Invalid API key"
            if response.status_code == 403:
                return False, "API key lacks required permissions"
            return False, f"Server returned status {response.status_code}"
        except httpx.ConnectError:
            return False, "Cannot connect to server. Check the URL is correct."
        except httpx.TimeoutException:
            return False, "Connection timed out. Check if server is accessible."
        except Exception as e:
            return False, f"Connection error: {str(e)[:100]}"

    def _build_payload(self, input_data: VideoUnderstandingInput) -> Dict[str, Any]:
        transcript = input_data.transcript_markdown or ""
        prompt = (
            "Analyze this video as research source material. "
            "Return strict JSON with keys summary, key_events, entities, and timeline. "
            "Each timeline item should include start_seconds, end_seconds, title, description. "
            "Each entity should include name, entity_type, description. "
            "Focus on visual events, scene changes, on-screen text, and actions."
        )
        if transcript:
            prompt += (
                "\n\nA transcript is available. Use it only as supporting context and "
                "prioritize visual evidence when they differ.\n\nTranscript:\n"
                f"{transcript[:12000]}"
            )

        return {
            "model": self.model_name,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_video", "video_url": input_data.url},
                    ],
                }
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "video_understanding",
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "summary": {"type": "string"},
                            "key_events": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "entities": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "name": {"type": "string"},
                                        "entity_type": {
                                            "type": ["string", "null"]
                                        },
                                        "description": {
                                            "type": ["string", "null"]
                                        },
                                    },
                                    "required": ["name", "entity_type", "description"],
                                },
                            },
                            "timeline": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "start_seconds": {
                                            "type": ["number", "null"]
                                        },
                                        "end_seconds": {
                                            "type": ["number", "null"]
                                        },
                                        "title": {"type": ["string", "null"]},
                                        "description": {"type": "string"},
                                    },
                                    "required": [
                                        "start_seconds",
                                        "end_seconds",
                                        "title",
                                        "description",
                                    ],
                                },
                            },
                        },
                        "required": ["summary", "key_events", "entities", "timeline"],
                    },
                }
            },
        }

    def _normalize_response(
        self, body: Dict[str, Any], *, transcript_used: bool
    ) -> VideoUnderstandingResult:
        payload = self._extract_json_payload(body)
        entities = [
            VideoEntity(
                name=item.get("name", "Unknown"),
                entity_type=item.get("entity_type"),
                description=item.get("description"),
            )
            for item in payload.get("entities", [])
        ]
        timeline = [
            VideoTimelineSegment(
                start_seconds=item.get("start_seconds"),
                end_seconds=item.get("end_seconds"),
                title=item.get("title"),
                description=item.get("description", ""),
            )
            for item in payload.get("timeline", [])
        ]
        return VideoUnderstandingResult(
            summary=payload.get("summary", "").strip() or "No summary returned.",
            key_events=_coerce_list(payload.get("key_events")),
            entities=entities,
            timeline=timeline,
            transcript_used=transcript_used,
            provider="openai_compatible",
            model=self.model_name,
            raw_response=body,
        )

    def _extract_json_payload(self, body: Dict[str, Any]) -> Dict[str, Any]:
        output = body.get("output", [])
        for item in output:
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    text = content.get("text")
                    if isinstance(text, str):
                        return json.loads(text)
        raise ValueError("Provider response did not contain structured output_text")


def _coerce_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]
