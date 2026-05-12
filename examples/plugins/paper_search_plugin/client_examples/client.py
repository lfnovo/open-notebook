from __future__ import annotations

import os
from uuid import uuid4

import httpx

BASE_URL = os.getenv("BASE_URL", "http://localhost:8099")
API_KEY = os.getenv("API_KEY", "dev-paper-key")


def headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {API_KEY}",
        "X-Lumina-Request-Id": str(uuid4()),
        "Content-Type": "application/json",
    }


def main() -> None:
    with httpx.Client(timeout=10) as client:
        search = client.post(
            f"{BASE_URL}/lumina/v1/sources/search",
            headers=headers(),
            json={"source_key": "paper_search", "query": "graph", "limit": 5},
        )
        search.raise_for_status()
        print("search:", search.json())

        item = search.json()["data"]["items"][0]
        fetch = client.post(
            f"{BASE_URL}/lumina/v1/sources/fetch",
            headers=headers(),
            json={"source_key": "paper_search", "external_id": item["external_id"]},
        )
        fetch.raise_for_status()
        print("fetch:", fetch.json())

        output = client.post(
            f"{BASE_URL}/lumina/v1/outputs/generate",
            headers=headers(),
            json={
                "source_key": "paper_search",
                "prompt": "Summarize the evidence.",
                "items": [item],
                "output_kind": "markdown",
                "options": {"async": True},
            },
        )
        output.raise_for_status()
        payload = output.json()
        print("generate:", payload)

        if payload["status"] == "accepted":
            job = client.get(
                f"{BASE_URL}/lumina/v1/jobs/{payload['external_job_id']}",
                headers=headers(),
            )
            job.raise_for_status()
            print("job:", job.json())


if __name__ == "__main__":
    main()
