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
        
    if response.status_code != 200:
        print(f"❌ Failed to start session: {data}")
        return
        
    session_id = data["session_id"]
    ws_url = data["ws_url"]
    print(f"✅ Session started. ID: {session_id}")
    print(f"2. Connecting to WebSocket: {ws_url}...")
    
    try:
        async with websockets.connect(ws_url) as ws:
            print("✅ WebSocket connected! Listening for events...")
            
            # Listen for 15 seconds or until we get a few comments
            comments = 0
            end_time = asyncio.get_event_loop().time() + 15.0
            
            while True:
                time_left = end_time - asyncio.get_event_loop().time()
                if time_left <= 0:
                    print("⏱️ 15s elapsed, stopping listening.")
                    break
                    
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=time_left)
                    event = json.loads(msg)
                    if event["type"] == "comment":
                        comments += 1
                        print(f"💬 [WS] {event['data']['author']}: {event['data']['text'][:60]}")
                    elif event["type"] == "session_status":
                        print(f"🔄 [WS] Status updated: {event['data']['status']}")
                    elif event["type"] == "stats":
                        pass # Ignore stats spam
                    else:
                        print(f"📥 [WS] Other event: {event['type']}")
                        
                    if comments >= 3:
                        print("🎯 Got 3 comments via WS! E2E test successful!")
                        break
                        
                except asyncio.TimeoutError:
                    pass
    except Exception as e:
        print(f"❌ WebSocket error: {e}")

asyncio.run(test_e2e())
