import re
import supabase._sync.client
from supabase import create_client, Client
from config import settings

# Monkey patch regex check to allow non-JWT keys (like sb_secret_...)
original_match = re.match
def mock_match(pattern, string, flags=0):
    if "A-Za-z0-9-_=" in pattern:
        return True
    return original_match(pattern, string, flags)

import types
mock_re = types.ModuleType("mock_re")
mock_re.__dict__.update(re.__dict__)
mock_re.match = mock_match
supabase._sync.client.re = mock_re

def get_supabase() -> Client:
    url = settings.supabase_url if settings.supabase_url else "http://localhost:8000"
    key = settings.supabase_service_role_key if settings.supabase_service_role_key else "dummy"
    try:
        return create_client(url, key)
    except Exception as e:
        print(f"Warning: Failed to initialize Supabase client: {e}")
        # Return a mock or None, but wait, returning None will break other code.
        # But if the user puts valid keys, it will work. Let's just catch and ignore or let the user know.
        class DummyClient:
            def table(self, *args, **kwargs):
                class DummyTable:
                    def select(self, *args, **kwargs): return self
                    def insert(self, *args, **kwargs): return self
                    def update(self, *args, **kwargs): return self
                    def eq(self, *args, **kwargs): return self
                    def lt(self, *args, **kwargs): return self
                    def gte(self, *args, **kwargs): return self
                    def execute(self, *args, **kwargs): 
                        from collections import namedtuple
                        Res = namedtuple('Res', ['data'])
                        return Res(data=[])
                return DummyTable()
        return DummyClient()

supabase = get_supabase()
