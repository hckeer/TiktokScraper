import logging
import asyncio
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from routers import sessions, ws, export
from routers.sessions import limiter
from config import settings
from services.supabase_client import supabase
from services.extraction_manager import manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s │ %(levelname)s │ %(message)s")

app = FastAPI(title="TikTok Live Extractor API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router)
app.include_router(ws.router)
app.include_router(export.router)

async def _start_default_sessions():
    usernames = [u.strip() for u in settings.default_tiktok_usernames.split(",") if u.strip()]
    if not usernames:
        return

    for username in usernames:
        session_id = f"autostart-{username}-{int(datetime.utcnow().timestamp())}"
        try:
            supabase.table("sessions").insert({
                "id": session_id,
                "tiktok_username": username,
                "status": "connecting",
                "client_ip": "system"
            }).execute()
        except Exception as e:
            logging.warning("Auto-start insert failed for %s: %s", username, e)

        try:
            await manager.start_session(username, session_id)
        except Exception as e:
            logging.error("Auto-start failed for %s: %s", username, e)
            try:
                supabase.table("sessions").update({"status": "error"}).eq("id", session_id).execute()
            except Exception:
                pass

@app.on_event("startup")
async def _startup():
    asyncio.create_task(_start_default_sessions())

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
