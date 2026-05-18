from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import uuid
from config import settings
from services.redis_client import limiter
from services.supabase_client import supabase
from services.extraction_manager import manager
import re

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

class SessionStartRequest(BaseModel):
    username: str

@router.post("")
@limiter.limit(f"{settings.rate_limit_per_hour}/hour")
async def start_session(request: Request, body: SessionStartRequest):
    username = body.username.strip()
    if "tiktok.com/" in username:
        match = re.search(r"@([\w.-]+)", username)
        if match:
            username = match.group(1)
        else:
            raise HTTPException(status_code=400, detail="Invalid TikTok URL")
    username = username.lstrip("@")
    
    session_id = str(uuid.uuid4())
    
    active_sessions = supabase.table("sessions").select("id", count="exact").eq("status", "connecting").execute()
    if active_sessions.count and active_sessions.count >= settings.max_global_sessions:
        raise HTTPException(status_code=429, detail="Maximum global sessions reached")
    
    try:
        supabase.table("sessions").insert({
            "id": session_id,
            "tiktok_username": username,
            "status": "connecting",
            "client_ip": request.client.host if request.client else "unknown"
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    try:
        await manager.start_session(username, session_id)
    except Exception as e:
        print(f"Session start error: {e}")
        supabase.table("sessions").update({"status": "error"}).eq("id", session_id).execute()
        raise HTTPException(status_code=500, detail=f"Failed to start session: {e}")
        
    return {
        "session_id": session_id,
        "ws_url": f"wss://{request.url.hostname}/ws/{session_id}" if request.url.hostname != "localhost" else f"ws://localhost:8000/ws/{session_id}"
    }

@router.get("/{session_id}")
async def get_session(session_id: str):
    res = supabase.table("sessions").select("*").eq("id", session_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Session not found")
    session = res.data[0]
    
    extraction = manager.get_session(session_id)
    if extraction:
        session.update(extraction.get_status())
        
    return session
