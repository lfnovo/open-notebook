import requests
import json
import time

# Based on your docker-compose, Ollama is at port 11435
OLLAMA_URL = "http://localhost:11435/api/generate"

def test_gpu_response():
    payload = {
        "model": "qwen2.5:1.5b",
        "prompt": "Write a short poem about a robot learning to paint.",
        "stream": False
    }

    print(f"Sending request to Qwen2.5:1.5b at {OLLAMA_URL}...")
    
    try:
        start_time = time.time()
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        end_time = time.time()
        
        result = response.json()
        
        print("\n--- Model Response ---")
        print(result.get("response"))
        print("----------------------")
        
        # Performance Metrics
        total_duration = end_time - start_time
        eval_count = result.get("eval_count", 0) # Number of tokens generated
        
        if eval_count > 0:
            tokens_per_sec = eval_count / (result.get("eval_duration") / 1e9)
            print(f"\nSpeed: {tokens_per_sec:.2f} tokens/sec")
            print(f"Total Time: {total_duration:.2f} seconds")
            
            # High tokens/sec (usually >30 for this model) indicates GPU is active.
            if tokens_per_sec > 20:
                print("✅ Status: High speed detected. Likely running on GPU.")
            else:
                print("⚠️ Status: Low speed. Check if 'runtime: nvidia' is working.")

    except requests.exceptions.ConnectionError:
        print("Error: Could not connect. Ensure 'docker compose up' is running.")

if __name__ == "__main__":
    test_gpu_response()
