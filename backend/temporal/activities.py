import asyncio
from datetime import datetime
from temporalio import activity
from config import settings
from services.supabase_client import supabase
from services.redis_client import publish_event
from extractor.extractor_wrapper import start_session
from extractor.extractor import PhoneExtractor
import pandas as pd
import openpyxl
import io

@activity.defn
async def connect_to_tiktok_live(username: str) -> str:
    # We use workflow id as session handle
    activity.heartbeat("Connecting")
    return activity.info().workflow_id

@activity.defn
async def stream_and_extract(username: str, session_id: str) -> dict:
    """Streams comments, extracts numbers, and publishes to Redis"""
    total_comments = 0
    total_numbers = 0
    print(f"[STREAM] Starting extraction for {username} (session: {session_id})")
    
    # We will use an asyncio event to listen for stop from the workflow if needed,
    # but Temporal can cancel activities. So we handle CancelledError.
    
    try:
        async for comment in start_session(username):
            activity.heartbeat(f"Processed {total_comments} comments")
            print(f"[COMMENT] {total_comments}: {comment.author} - {comment.text[:50]}")
            
            # Publish comment
            await publish_event(session_id, "comment", {
                "text": comment.text,
                "author": comment.author,
                "timestamp": int(comment.timestamp.timestamp() * 1000)
            })
            total_comments += 1
            
            # Extract phones
            phones = PhoneExtractor.extract(comment.text)
            if phones:
                print(f"[PHONE] Found: {phones}")
                for phone in phones:
                    # Publish phone
                    await publish_event(session_id, "phone_found", {
                        "number": phone,
                        "comment": comment.text,
                        "timestamp": int(comment.timestamp.timestamp() * 1000)
                    })
                    total_numbers += 1
                    
                # We could persist here or batch. Let's do it directly for simplicity or in batches.
                try:
                    data = [{"session_id": session_id, "phone_number": p, "source_comment": comment.text} for p in phones]
                    supabase.table("extracted_numbers").insert(data).execute()
                except Exception as e:
                    print(f"Error inserting: {e}")
                    
            await publish_event(session_id, "stats", {
                "total_comments": total_comments,
                "total_numbers": total_numbers
            })
            
    except asyncio.CancelledError:
        print(f"[STREAM] Activity cancelled for {username}")
        
    print(f"[STREAM] Finished for {username}: {total_comments} comments, {total_numbers} numbers")
    return {"total_comments": total_comments, "total_numbers": total_numbers}

@activity.defn
async def update_session_status(session_id: str, status: str, total_comments: int = 0, total_numbers: int = 0) -> None:
    activity.heartbeat(f"Updating status to {status}")
    data = {
        "status": status,
        "total_comments": total_comments,
        "total_numbers": total_numbers
    }
    if status in ("ended", "error"):
        data["ended_at"] = datetime.now().isoformat()
    try:
        supabase.table("sessions").update(data).eq("id", session_id).execute()
        await publish_event(session_id, "session_status", {"status": status})
    except Exception as e:
        print(f"Error updating session status: {e}")

@activity.defn
async def export_csv_activity(session_id: str) -> bytes:
    res = supabase.table("extracted_numbers").select("*").eq("session_id", session_id).execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        return b""
    # Return as UTF-8 BOM
    return b'\xef\xbb\xbf' + df.to_csv(index=False).encode('utf-8')

@activity.defn
async def export_excel_activity(session_id: str) -> bytes:
    res = supabase.table("extracted_numbers").select("*").eq("session_id", session_id).execute()
    df = pd.DataFrame(res.data)
    output = io.BytesIO()
    if not df.empty:
        df.to_excel(output, index=False)
    return output.getvalue()
