import httpx
import sys

def main():
    base_url = "http://localhost:5055"
    
    # 1. Create the model
    print("Creating embedding model...")
    resp = httpx.post(f"{base_url}/api/models", json={
        "name": "nvidia/nv-embedqa-e5-v5",
        "provider": "openai_compatible",
        "type": "embedding"
    })
    
    if resp.status_code == 400 and "already exists" in resp.text:
        print("Model already exists. Fetching it...")
        models = httpx.get(f"{base_url}/api/models").json()
        model_id = next((m["id"] for m in models if m["name"] == "nvidia/nv-embedqa-e5-v5" and m["type"] == "embedding"), None)
        if not model_id:
            print("Failed to find existing model ID")
            sys.exit(1)
    elif resp.status_code == 200:
        model_id = resp.json()["id"]
        print(f"Created model with ID: {model_id}")
    else:
        print(f"Failed to create model: {resp.status_code} {resp.text}")
        sys.exit(1)
        
    # 2. Set as default
    print(f"Setting {model_id} as default embedding model...")
    resp = httpx.put(f"{base_url}/api/models/defaults", json={
        "default_embedding_model": model_id
    })
    
    if resp.status_code == 200:
        print("Successfully set default embedding model!")
    else:
        print(f"Failed to set default: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    main()
