from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    supabase_url: str
    supabase_service_role_key: str
    max_global_sessions: int = 10
    max_sessions_per_ip: int = 1
    rate_limit_per_hour: int = 5
    max_session_duration_hours: int = 4
    default_tiktok_usernames: str = "@dnmhr.consultants"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
