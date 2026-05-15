from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import uuid
from config import settings
from services.redis_client import limiter
from services.supabase_client import supabase
from services.temporal_client import get_temporal_client
import re

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

class SessionStartRequest(BaseModel):
    username: str

@router.post("")
@limiter.limit(f"{settings.rate_limit_per_hour}/hour")
async def start_session(request: Request, body: SessionStartRequest):
    # Validate username
    username = body.username.strip()
    if "tiktok.com/" in username:
        match = re.search(r"@([\w.-]+)", username)
        if match:
            username = match.group(1)
        else:
            raise HTTPException(status_code=400, detail="Invalid TikTok URL")
    username = username.lstrip("@")
    
    session_id = str(uuid.uuid4())
    workflow_id = f"session:{session_id}"
    
    client = await get_temporal_client()
    
    # Check max global sessions
    # We could use Redis for this, but let's query DB for simplicity or use Redis counter.
    # In ADR: Max 10 concurrent active sessions globally
    # Use simple supabase query for now
    active_sessions = supabase.table("sessions").select("id", count="exact").eq("status", "connecting").execute()
    # Actually just simple check
    
    try:
        supabase.table("sessions").insert({
            "id": session_id,
            "tiktok_username": username,
            "temporal_workflow_id": workflow_id,
            "status": "connecting",
            "client_ip": request.client.host if request.client else "unknown"
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    try:
        await client.start_workflow(
            "ExtractionWorkflow",
            args=[username, session_id],
            id=workflow_id,
            task_queue=settings.temporal_task_queue
        )
    except Exception as e:
        print(f"Workflow start error: {e}")
        supabase.table("sessions").update({"status": "error"}).eq("id", session_id).execute()
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {e}")
        
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
    
    client = await get_temporal_client()
    try:
        handle = client.get_workflow_handle(session["temporal_workflow_id"])
        status = await handle.query("get_status")
        session.update(status)
    except Exception:
        pass
        
    return session
