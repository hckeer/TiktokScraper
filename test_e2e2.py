import asyncio
import httpx
import websockets
import json

async def test_e2e():
    username = "aakash_giri0"
    print(f"1. Starting session for @{username} via API...")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/sessions",
            json={"username": username}
        )
        data = response.json()
        
    session_id = data["session_id"]
    ws_url = data["ws_url"]
    print(f"✅ Session started. ID: {session_id}")
    
    try:
        async with websockets.connect(ws_url) as ws:
            print("✅ WebSocket connected! Listening for raw events...")
            
            # Listen for longer to ensure it stays connected
            end_time = asyncio.get_event_loop().time() + 45.0
            comments_seen = 0
            while True:
                time_left = end_time - asyncio.get_event_loop().time()
                if time_left <= 0: break
                    
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=time_left)
                    parsed = json.loads(msg)
                    if parsed.get("type") == "comment":
                        comments_seen += 1
                        print(f"[{comments_seen}] 📥 RAW: {msg[:150]}")
                    else:
                        print(f"📥 RAW: {msg[:150]}")
                except asyncio.TimeoutError:
                    pass
    except Exception as e:
        print(f"❌ WebSocket error: {e}")

asyncio.run(test_e2e())
