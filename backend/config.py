from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    supabase_url: str
    supabase_service_role_key: str
    temporal_host: str = "temporal:7233"
    temporal_namespace: str = "tiklive"
    temporal_task_queue: str = "extraction-queue"
    redis_url: str = "redis://redis:6379/0"
    max_global_sessions: int = 10
    max_sessions_per_ip: int = 1
    rate_limit_per_hour: int = 5
    max_session_duration_hours: int = 4
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
