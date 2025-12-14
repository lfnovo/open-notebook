#!/usr/bin/env python3
import subprocess
import json

# Get all unembedded sources
result = subprocess.run(
    ["curl", "-s", "http://localhost:5055/api/sources?limit=500"],
    capture_output=True,
    text=True
)

if result.returncode == 0:
    try:
        data = json.loads(result.stdout)
        # Handle both list and dict responses
        sources = data if isinstance(data, list) else data.get("sources", [])
        unembedded = [s for s in sources if isinstance(s, dict) and not s.get("embedded", False)]
        
        print(f"Sources without embeddings ({len(unembedded)}):")
        print()
        for s in unembedded[:50]:
            print(f"  • {s.get('title', 'Untitled')} (ID: {s.get('id', 'unknown')})")
        
        if len(unembedded) > 50:
            print(f"  ... and {len(unembedded) - 50} more")
        
        print("\n✓ These sources had stuck embed_chunk jobs and need to be re-uploaded for fresh embedding.")
        
    except json.JSONDecodeError as e:
        print(f"Error parsing response: {e}")
        print("Raw response:", result.stdout[:200])
else:
    print(f"Error: {result.stderr}")
