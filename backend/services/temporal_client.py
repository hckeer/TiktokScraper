from temporalio.client import Client
from config import settings

_temporal_client = None

async def get_temporal_client() -> Client:
    global _temporal_client
    if _temporal_client is None:
        try:
            _temporal_client = await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)
        except Exception:
            # Fallback for local testing if namespace doesn't exist
            _temporal_client = await Client.connect(settings.temporal_host, namespace="default")
    return _temporal_client
