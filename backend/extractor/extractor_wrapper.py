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

def _safe_get_username(event) -> str:
    try:
        user_info = getattr(event, 'user_info', None)
        if user_info is not None:
            pydict = user_info.to_pydict() if hasattr(user_info, 'to_pydict') else {}
            for key in ('unique_id', 'uniqueId', 'display_id', 'displayId', 'nickname', 'nickName'):
                if key in pydict and pydict[key]:
                    return pydict[key]
            return str(user_info)
    except Exception:
        pass
    try:
        user = getattr(event, 'user', None)
        if user is not None:
            return getattr(user, 'unique_id', None) or getattr(user, 'uniqueId', None) or str(user)
    except Exception:
        pass
    return "unknown_user"

async def start_session(username: str) -> AsyncGenerator[Comment, None]:
    print(f"[EXTRACTOR] Connecting to {username}...")
    client = TikTokLiveClient(
        unique_id=username,
        web_kwargs={
            "curl_cffi_kwargs": {"impersonate": "chrome110"}
        }
    )
    from collections import OrderedDict
    queue = asyncio.Queue()
    comment_received_count = 0
    seen_messages = OrderedDict()

    @client.on(CommentEvent)
    async def on_comment(event: CommentEvent):
        nonlocal comment_received_count
        
        author = _safe_get_username(event)
        msg_id = getattr(event, "msg_id", None) or f"{author}_{event.comment}"
        if msg_id in seen_messages:
            return
        seen_messages[msg_id] = True
        if len(seen_messages) > 1000:
            seen_messages.popitem(last=False)
            
        comment_received_count += 1
        print(f"[EXTRACTOR] Comment #{comment_received_count} from {author}: {event.comment[:50]}")
        comment = Comment(
            author=author,
            text=event.comment,
            timestamp=datetime.now()
        )
        await queue.put(comment)

    @client.on(DisconnectEvent)
    async def on_disconnect(event: DisconnectEvent):
        print(f"[EXTRACTOR] Disconnected from {username}")

    async def safe_start():
        while True:
            try:
                print(f"[EXTRACTOR] Starting client.start() for {username}...")
                client_task = await client.start()
                if isinstance(client_task, asyncio.Task):
                    await client_task
                print(f"[EXTRACTOR] client task completed for {username}")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"[EXTRACTOR] client.start() error for {username}: {type(e).__name__}: {e}")
                await asyncio.sleep(5)
    
    task = asyncio.create_task(safe_start())
    
    try:
        while True:
            get_task = asyncio.create_task(queue.get())
            done, pending = await asyncio.wait(
                [get_task, task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            if task in done:
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
        print(f"[EXTRACTOR] CancelledError for {username}, disconnecting...")
        try:
            await client.disconnect()
        except Exception:
            pass
        task.cancel()
        raise
