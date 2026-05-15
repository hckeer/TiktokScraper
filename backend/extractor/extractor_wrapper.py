import asyncio
import traceback
from datetime import datetime
from typing import AsyncGenerator
from pydantic import BaseModel
from .extractor import PhoneExtractor, CommentData
from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent, ConnectEvent, DisconnectEvent

class Comment(BaseModel):
    author: str
    text: str
    timestamp: datetime

async def start_session(username: str) -> AsyncGenerator[Comment, None]:
    print(f"[EXTRACTOR] Connecting to {username}...")
    # Use curl_cffi to bypass TikTok TLS blocking
    client = TikTokLiveClient(
        unique_id=username,
        web_kwargs={
            "curl_cffi_kwargs": {"impersonate": "chrome110"}
        }
    )
    queue = asyncio.Queue()
    comment_received_count = 0
    seen_messages = set()  # Prevent duplicates on reconnect

    @client.on(CommentEvent)
    async def on_comment(event: CommentEvent):
        nonlocal comment_received_count
        
        # Avoid duplicates on reconnect
        msg_id = getattr(event, "msg_id", None) or f"{event.user.unique_id}_{event.comment}"
        if msg_id in seen_messages:
            return
        seen_messages.add(msg_id)
        if len(seen_messages) > 1000:
            seen_messages.pop() # Keep memory bounded
            
        comment_received_count += 1
        print(f"[EXTRACTOR] Comment #{comment_received_count} from {event.user.unique_id}: {event.comment[:50]}")
        # We put the comment in the queue
        comment = Comment(
            author=event.user.unique_id,
            text=event.comment,
            timestamp=datetime.now()
        )
        await queue.put(comment)

    @client.on(DisconnectEvent)
    async def on_disconnect(event: DisconnectEvent):
        print(f"[EXTRACTOR] Disconnected from {username}")

    # We start the client in a background task
    async def safe_start():
        while True:
            try:
                print(f"[EXTRACTOR] Starting client.start() for {username}...")
                client_task = await client.start()
                if isinstance(client_task, asyncio.Task):
                    await client_task
                print(f"[EXTRACTOR] client task completed for {username}")
                # If it completes cleanly, wait a bit and reconnect
                await asyncio.sleep(5)
            except Exception as e:
                print(f"[EXTRACTOR] client.start() error for {username}: {type(e).__name__}: {e}")
                # Wait before auto-reconnecting
                await asyncio.sleep(5)
    
    task = asyncio.create_task(safe_start())
    
    try:
        while True:
            # Yield comments as they arrive, but also check if task failed
            get_task = asyncio.create_task(queue.get())
            done, pending = await asyncio.wait(
                [get_task, task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            if task in done:
                # Client stopped or crashed permanently (shouldn't happen due to while True loop above)
                exc = task.exception()
                if exc:
                    print(f"[EXTRACTOR] TikTok client fatal error: {exc}")
                    traceback.print_exception(type(exc), exc, exc.__traceback__)
                print(f"[EXTRACTOR] Fatal task completion for {username}")
                break
                
            if get_task in done:
                comment = get_task.result()
                yield comment
                
    except asyncio.CancelledError:
        # Client stop should be invoked on cancel
        print(f"[EXTRACTOR] CancelledError for {username}, disconnecting...")
        try:
            await client.disconnect()
        except Exception:
            pass
        task.cancel()
        raise
