from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.supabase_client import supabase
from services.extraction_manager import manager
import asyncio
import json

router = APIRouter(prefix="/ws", tags=["websocket"])

@router.websocket("/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    print(f"[WS] Client connected for session: {session_id}")

    manager.register_ws(session_id, websocket)

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
        manager.unregister_ws(session_id, websocket)
        print(f"[WS] Connection closed for {session_id}")
