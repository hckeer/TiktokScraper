import asyncio
import csv
import logging
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Set, List
from fastapi import WebSocket

from extractor.extractor_wrapper import start_session
from extractor.extractor import PhoneExtractor
from services.supabase_client import supabase

logger = logging.getLogger(__name__)


def _normalize_username(value: str) -> str:
    username = value.strip()
    if "tiktok.com/" in username:
        match = re.search(r"@([\w.-]+)", username)
        if match:
            username = match.group(1)
    return username.lstrip("@")


class ExtractionSession:
    """Manages a single TikTok extraction session."""

    def __init__(self, username: str, session_id: str):
        self.username = _normalize_username(username) or username.strip()
        self.session_id = session_id
        self.status = "connecting"
        self.total_comments = 0
        self.total_numbers = 0
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._ws_clients: Set[WebSocket] = set()
        self._csv_lock = asyncio.Lock()
        self._csv_headers = [
            "timestamp",
            "session_id",
            "tiktok_username",
            "tiktok_profile_url",
            "author",
            "comment_text",
            "phones"
        ]
        self._csv_dir = Path(__file__).resolve().parents[1] / "exports"
        self._csv_dir.mkdir(parents=True, exist_ok=True)
        self._csv_path = self._csv_dir / f"session_{self.session_id}.csv"
        self._profile_url = f"https://www.tiktok.com/@{self.username}" if self.username else ""

    def add_ws(self, ws: WebSocket):
        self._ws_clients.add(ws)

    def remove_ws(self, ws: WebSocket):
        self._ws_clients.discard(ws)

    async def broadcast(self, event_type: str, data: dict):
        message = json.dumps({"type": event_type, **data})
        dead = set()
        for ws in self._ws_clients:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        self._ws_clients -= dead

    async def start(self):
        self._task = asyncio.create_task(self._run())

    async def _run(self):
        try:
            self.status = "connecting"
            await self._update_status("connecting")
            logger.info(f"[SESSION] Connecting to {self.username} (session: {self.session_id})")

            self.status = "live"
            await self._update_status("live")
            logger.info(f"[SESSION] Live: {self.username}")

            async for comment in start_session(self.username):
                if self._stop_event.is_set():
                    break

                self.total_comments += 1
                logger.info(f"[COMMENT] #{self.total_comments} {comment.author}: {comment.text[:50]}")

                phones = PhoneExtractor.extract(comment.text)
                await self._append_csv(comment, phones)

                await self.broadcast("comment", {
                    "text": comment.text,
                    "author": comment.author,
                    "timestamp": int(comment.timestamp.timestamp() * 1000)
                })

                if phones:
                    logger.info(f"[PHONE] Found: {phones}")
                    for phone in phones:
                        await self.broadcast("phone_found", {
                            "number": phone,
                            "comment": comment.text,
                            "timestamp": int(comment.timestamp.timestamp() * 1000)
                        })
                        self.total_numbers += 1

                    try:
                        data = [
                            {"session_id": self.session_id, "phone_number": p, "source_comment": comment.text}
                            for p in phones
                        ]
                        supabase.table("extracted_numbers").insert(data).execute()
                    except Exception as e:
                        logger.error(f"Error inserting: {e}")

                await self.broadcast("stats", {
                    "total_comments": self.total_comments,
                    "total_numbers": self.total_numbers
                })

        except asyncio.CancelledError:
            logger.info(f"[SESSION] Cancelled for {self.username}")
        except Exception as e:
            logger.error(f"[SESSION] Error for {self.username}: {e}")
            self.status = "error"
            await self._update_status("error")
            return

        self.status = "ended"
        await self._update_status("ended")
        logger.info(f"[SESSION] Finished {self.username}: {self.total_comments} comments, {self.total_numbers} numbers")

    async def _append_csv(self, comment, phones: List[str]):
        row = {
            "timestamp": comment.timestamp.isoformat(),
            "session_id": self.session_id,
            "tiktok_username": self.username,
            "tiktok_profile_url": self._profile_url,
            "author": comment.author,
            "comment_text": comment.text,
            "phones": ",".join(phones)
        }
        try:
            async with self._csv_lock:
                await asyncio.to_thread(self._write_csv_row, row)
        except Exception as e:
            logger.error("CSV write failed for session %s: %s", self.session_id, e)

    def _write_csv_row(self, row: dict):
        needs_header = True
        if self._csv_path.exists():
            try:
                needs_header = self._csv_path.stat().st_size == 0
            except Exception:
                needs_header = False
        with self._csv_path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=self._csv_headers)
            if needs_header:
                writer.writeheader()
            writer.writerow(row)
            file.flush()

    async def stop(self):
        self._stop_event.set()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _update_status(self, status: str):
        self.status = status
        data = {
            "status": status,
            "total_comments": self.total_comments,
            "total_numbers": self.total_numbers
        }
        if status in ("ended", "error"):
            data["ended_at"] = datetime.now().isoformat()
        try:
            supabase.table("sessions").update(data).eq("id", self.session_id).execute()
            await self.broadcast("session_status", {"status": status})
        except Exception as e:
            logger.error(f"Error updating status: {e}")

    def get_status(self) -> dict:
        return {
            "status": self.status,
            "total_comments": self.total_comments,
            "total_numbers": self.total_numbers
        }


class ExtractionManager:
    """Global manager for all extraction sessions."""

    def __init__(self):
        self._sessions: Dict[str, ExtractionSession] = {}
        self._lock = asyncio.Lock()

    async def start_session(self, username: str, session_id: str) -> ExtractionSession:
        async with self._lock:
            session = ExtractionSession(username, session_id)
            self._sessions[session_id] = session
        await session.start()
        return session

    async def stop_session(self, session_id: str):
        async with self._lock:
            session = self._sessions.get(session_id)
        if session:
            await session.stop()

    def get_session(self, session_id: str) -> Optional[ExtractionSession]:
        return self._sessions.get(session_id)

    def register_ws(self, session_id: str, ws: WebSocket):
        session = self._sessions.get(session_id)
        if session:
            session.add_ws(ws)
            logger.info(f"[WS] Registered for session {session_id} (total clients: {len(session._ws_clients)})")

    def unregister_ws(self, session_id: str, ws: WebSocket):
        session = self._sessions.get(session_id)
        if session:
            session.remove_ws(ws)
            logger.info(f"[WS] Unregistered for session {session_id} (total clients: {len(session._ws_clients)})")


manager = ExtractionManager()
