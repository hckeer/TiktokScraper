from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.supabase_client import supabase
from services.redis_client import redis_client
from services.extraction_manager import manager
import asyncio
import json

router = APIRouter(prefix="/ws", tags=["websocket"])

@router.websocket("/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    print(f"[WS] Client connected for session: {session_id}")
    
    channel_name = f"session:{session_id}:events"
    
    redis_sub = redis_client.pubsub()
    await redis_sub.subscribe(channel_name)
    print(f"[WS] Subscribed to channel: {channel_name}")
    
    async def redis_reader():
        print(f"[WS] Redis reader started for {channel_name}")
        try:
            async for message in redis_sub.listen():
                print(f"[WS] Message type check: {message.get('type')}")
                if message["type"] == "message":
                    print(f"[WS] Received message on {channel_name}: {message['data'][:100]}")
                    try:
                        await websocket.send_text(message["data"])
                        print(f"[WS] Sent message to client successfully")
                    except Exception as e:
                        print(f"[WS] Error sending to websocket: {e}")
                        break
        except asyncio.CancelledError:
            print(f"[WS] Redis reader cancelled for {channel_name}")
        except Exception as e:
            print(f"[WS] Redis reader error: {e}")

    reader_task = asyncio.create_task(redis_reader())
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("type") == "stop":
                try:
                    await manager.stop_session(session_id)
                except Exception as e:
                    print(f"Error stopping session: {e}")
            elif message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        print(f"[WS] Client disconnected: {session_id}")
    except Exception as e:
        print(f"[WS] WebSocket error: {e}")
    finally:
        reader_task.cancel()
        try:
            await redis_sub.unsubscribe(channel_name)
            await redis_sub.close()
        except:
            pass
        print(f"[WS] Connection closed for {session_id}")
