import asyncio
from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent, ConnectEvent

async def test_real_stream():
    username = "aakash_giri0"
    print(f"🔴 Testing on host: @{username}")
    
    client = TikTokLiveClient(unique_id=username)
    
    @client.on(ConnectEvent)
    async def on_connect(event):
        print(f"✅ CONNECTED!")
    
    @client.on(CommentEvent)
    async def on_comment(event):
        print(f"💬 COMMENT: @{event.user.unique_id} -> {event.comment[:80]}")
    
    try:
        task = await client.start()
        await asyncio.wait_for(task, timeout=30)
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

asyncio.run(test_real_stream())
