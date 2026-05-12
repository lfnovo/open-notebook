from __future__ import annotations

import asyncio
from typing import Any, Optional
from uuid import uuid4

import httpx

from open_notebook.exceptions import ExternalServiceError, NetworkError


class ExternalApiClient:
    """HTTP client for Lumina third-party API plugins."""

    def __init__(self, *, base_url: str, api_key: str, timeout_seconds: int = 30):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def _headers(self, request_id: Optional[str] = None) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-Lumina-Request-Id": request_id or str(uuid4()),
            "Content-Type": "application/json",
        }

    async def get_manifest(self) -> dict[str, Any]:
        return await self._get("/.well-known/lumina-plugin.json")

    async def health(self) -> dict[str, Any]:
        return await self._get("/lumina/v1/health")

    async def search_sources(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post("/lumina/v1/sources/search", payload)

    async def fetch_source(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post("/lumina/v1/sources/fetch", payload)

    async def generate_output(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post("/lumina/v1/outputs/generate", payload)

    async def get_job(self, external_job_id: str) -> dict[str, Any]:
        return await self._get(f"/lumina/v1/jobs/{external_job_id}")

    async def wait_for_result(
        self,
        initial_response: dict[str, Any],
        *,
        max_polls: int = 30,
        default_delay_seconds: float = 2.0,
    ) -> dict[str, Any]:
        status = initial_response.get("status")
        if status in {"completed", "failed"}:
            return initial_response
        if status != "accepted":
            raise ExternalServiceError("External API returned an invalid async status")

        external_job_id = initial_response.get("external_job_id")
        if not external_job_id:
            raise ExternalServiceError("External API accepted request without external_job_id")

        response = initial_response
        for _ in range(max_polls):
            delay = float(response.get("next_poll_after_seconds") or default_delay_seconds)
            await asyncio.sleep(max(0.0, delay))
            response = await self.get_job(str(external_job_id))
            if response.get("status") in {"completed", "failed"}:
                return response

        raise TimeoutError("External API job polling timed out")

    async def _get(self, path: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(
                    f"{self.base_url}{path}",
                    headers=self._headers(),
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise ExternalServiceError(
                f"External API returned HTTP {exc.response.status_code}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise TimeoutError("External API request timed out") from exc
        except httpx.RequestError as exc:
            raise NetworkError(f"External API request failed: {exc}") from exc

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}{path}",
                    json=payload,
                    headers=self._headers(),
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise ExternalServiceError(
                f"External API returned HTTP {exc.response.status_code}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise TimeoutError("External API request timed out") from exc
        except httpx.RequestError as exc:
            raise NetworkError(f"External API request failed: {exc}") from exc
