#!/usr/bin/env python3
"""
Test script to verify real-time streaming from chat endpoint.
Run this to verify tokens are streaming immediately, not buffered.
"""
import asyncio
import json
import httpx
import time
from datetime import datetime


async def test_streaming():
    """Test the /chat/stream-execute endpoint directly."""
    
    # Create a fake notebook and session for testing
    api_url = "http://localhost:5055/api"
    
    print("=" * 80)
    print(f"🧪 STREAMING TEST - {datetime.now().isoformat()}")
    print("=" * 80)
    
    # For testing, we'll use an existing session or create one
    # First, let's get or create a notebook
    
    try:
        # Test with a simple request
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Create a test session first
            print("\n1️⃣  Creating test session...")
            
            session_response = await client.post(
                f"{api_url}/chat/sessions",
                json={
                    "notebook_id": "notebook:test-streaming",
                    "title": "Streaming Test"
                }
            )
            
            if session_response.status_code != 200:
                print(f"❌ Failed to create session: {session_response.status_code}")
                print(session_response.text)
                return
            
            session_data = session_response.json()
            session_id = session_data["id"]
            print(f"✅ Session created: {session_id}")
            
            # Now test streaming
            print("\n2️⃣  Testing streaming endpoint /chat/stream-execute...")
            print("   Sending: 'Write me a funny haiku in 3 lines'\n")
            
            stream_url = f"{api_url}/chat/stream-execute"
            
            # Track timing
            start_time = time.time()
            token_times = []
            accumulated = ""
            
            async with client.stream(
                "POST",
                stream_url,
                json={
                    "session_id": session_id,
                    "message": "Write me a funny haiku in 3 lines",
                    "context": None
                }
            ) as response:
                
                if response.status_code != 200:
                    print(f"❌ Stream failed: {response.status_code}")
                    async for line in response.aiter_lines():
                        print(f"   {line}")
                    return
                
                print("📡 Streaming started (tokens should appear immediately below):")
                print("─" * 60)
                
                buffer = ""
                token_count = 0
                last_output_time = start_time
                
                async for line in response.aiter_lines():
                    current_time = time.time()
                    elapsed = current_time - start_time
                    
                    line = line.strip()
                    if not line or line.startswith(":"):
                        continue
                    
                    if line.startswith("data: "):
                        try:
                            json_str = line[6:]
                            event = json.loads(json_str)
                            
                            if "token" in event:
                                token = event["token"]
                                token_count += 1
                                accumulated += token
                                
                                # Record timing
                                time_since_last = current_time - last_output_time
                                token_times.append(time_since_last)
                                last_output_time = current_time
                                
                                # Print token immediately
                                print(token, end="", flush=True)
                                
                                # Every 10 tokens, show timing info
                                if token_count % 10 == 0:
                                    avg_interval = sum(token_times[-10:]) / 10 if token_times else 0
                                    print(f" [{token_count}@{avg_interval:.3f}s/token]", end="", flush=True)
                            
                            elif event.get("done"):
                                print(f"\n{'─' * 60}")
                                print(f"\n✅ STREAMING COMPLETE")
                                print(f"   Total tokens: {token_count}")
                                print(f"   Total length: {len(accumulated)} chars")
                                print(f"   Total time: {elapsed:.2f}s")
                                if token_count > 0:
                                    print(f"   Avg token time: {elapsed/token_count:.4f}s/token")
                                    print(f"   Tokens per second: {token_count/elapsed:.1f} t/s")
                                
                                # Analyze inter-token timing
                                if token_times:
                                    min_interval = min(token_times)
                                    max_interval = max(token_times)
                                    avg_interval = sum(token_times) / len(token_times)
                                    print(f"\n   Token arrival intervals:")
                                    print(f"   - Min: {min_interval:.4f}s")
                                    print(f"   - Max: {max_interval:.4f}s")
                                    print(f"   - Avg: {avg_interval:.4f}s")
                                    
                                    # Check if buffering (all tokens at once = single spike)
                                    if len(token_times) > 3:
                                        first_batch = sum(1 for t in token_times[:5] if t < 0.01)
                                        if first_batch == len(token_times[:5]):
                                            print(f"\n   ⚠️  WARNING: Tokens arrived in bursts (possible buffering)")
                                        else:
                                            print(f"\n   ✨ Tokens streaming smoothly!")
                                
                                return
                            
                            elif "error" in event:
                                print(f"\n❌ Stream error: {event['error']}")
                                return
                        
                        except json.JSONDecodeError:
                            print(f"\n⚠️  Could not parse: {line}")
                
                print(f"\n{'─' * 60}")
                print(f"Stream ended. Accumulated response: {len(accumulated)} chars")
    
    except asyncio.TimeoutError:
        print("❌ Request timeout - streaming took too long")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n🚀 Running streaming test...\n")
    asyncio.run(test_streaming())
    print("\n" + "=" * 80)
