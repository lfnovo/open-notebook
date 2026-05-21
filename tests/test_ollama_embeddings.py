"""Test Ollama embeddings API endpoint."""
import requests


def test_ollama_embeddings(
    base_url: str = "http://localhost:11434",
    model: str = "nomic-embed-text",
    prompt: str = "Your text goes here",
) -> dict:
    """Send a POST request to Ollama embeddings API and return the response."""
    response = requests.post(
        f"{base_url}/api/embeddings",
        json={"model": model, "prompt": prompt},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    result = test_ollama_embeddings()
    print(f"Model: {result.get('model')}")
    print(f"Embedding dim: {len(result.get('embedding', []))}")
    print(f"First 5 values: {result.get('embedding', [])[:5]}")