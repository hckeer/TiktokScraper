import redis.asyncio as redis
from slowapi import Limiter
from slowapi.util import get_remote_address
from config import settings
import json

redis_client = redis.from_url(settings.redis_url, decode_responses=True)
limiter = Limiter(key_func=get_remote_address)

async def publish_event(session_id: str, event_type: str, data: dict):
    channel = f"session:{session_id}:events"
    message = json.dumps({"type": event_type, **data})
    await redis_client.publish(channel, message)
