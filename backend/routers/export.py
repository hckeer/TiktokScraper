from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from services.supabase_client import supabase
import io

router = APIRouter(prefix="/api/sessions/{session_id}/export", tags=["export"])

@router.get("/csv")
async def export_csv(session_id: str):
    res = supabase.table("sessions").select("*").eq("id", session_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Session not found")
        
    res = supabase.table("extracted_numbers").select("*").eq("session_id", session_id).execute()
    import pandas as pd
    df = pd.DataFrame(res.data)
    if df.empty:
        return StreamingResponse(io.BytesIO(b""), media_type="text/csv")
    
    output = b'\xef\xbb\xbf' + df.to_csv(index=False).encode('utf-8')
    return StreamingResponse(io.BytesIO(output), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=export_{session_id}.csv"})

@router.get("/excel")
async def export_excel(session_id: str):
    res = supabase.table("sessions").select("*").eq("id", session_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Session not found")
        
    res = supabase.table("extracted_numbers").select("*").eq("session_id", session_id).execute()
    import pandas as pd
    df = pd.DataFrame(res.data)
    output = io.BytesIO()
    if not df.empty:
        df.to_excel(output, index=False)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue()), 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        headers={"Content-Disposition": f"attachment; filename=export_{session_id}.xlsx"}
    )
