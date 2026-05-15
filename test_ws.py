import asyncio
import websockets

async def test():
    try:
        async with websockets.connect("ws://localhost:8000/ws/invalid-session") as ws:
            pass
    except Exception as e:
        print("Exception:", e)

asyncio.run(test())
