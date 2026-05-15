import os
import asyncio
from supabase import create_client

url = "https://mtusxullmgsjxhpsnhwy.supabase.co"
key = "sb_secret_ybGAsSnzwKU_tpi3rs1-iw_OQOp24Tl"
supabase = create_client(url, key)

res = supabase.table("sessions").select("*").execute()
print(res.data)
