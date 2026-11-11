import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from supabase import Client, create_client

API_KEY = os.getenv("CLOUD_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")

app = FastAPI(title="AI-Enhanced-HFT Cloud API", version="0.2.0")


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
        raise RuntimeError("Supabase is not configured; set SUPABASE_URL and SUPABASE_SECRET_KEY")
    return create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)


def require_key(authorization: str | None = Header(default=None)):
    if not API_KEY:
        raise HTTPException(status_code=503, detail="Cloud API key is not configured")
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Invalid API credentials")


class Telemetry(BaseModel):
    account_login: str | None = None
    server: str | None = None
    symbol: str
    timeframe: str
    bid: float | None = None
    ask: float | None = None
    spread_points: float | None = None
    balance: float | None = None
    equity: float | None = None
    margin: float | None = None
    free_margin: float | None = None
    positions_count: int = 0
    positions: list[dict[str, Any]] = Field(default_factory=list)
    bars: list[dict[str, Any]] = Field(default_factory=list)
    indicators: dict[str, Any] = Field(default_factory=dict)
    ea_status: str = "running"
    terminal_time: str | None = None


class Event(BaseModel):
    severity: str = "INFO"
    event_type: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
def health():
    try:
        get_supabase().table("telemetry").select("id").limit(1).execute()
        return {
            "status": "ok",
            "database": "connected",
            "service": "ai-enhanced-hft-api",
            "time": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Supabase connection/table check failed: {exc}")


@app.post("/v1/telemetry", dependencies=[Depends(require_key)])
def ingest_telemetry(item: Telemetry):
    now = datetime.now(timezone.utc).isoformat()
    payload = item.model_dump()
    try:
        result = get_supabase().table("telemetry").insert({
            "received_at": now,
            "account_login": item.account_login,
            "server": item.server,
            "symbol": item.symbol,
            "timeframe": item.timeframe,
            "payload": payload,
        }).execute()
        inserted = result.data[0] if result.data else {}
        return {"accepted": True, "telemetry_id": inserted.get("id"), "received_at": now}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Telemetry storage failed: {exc}")


@app.post("/v1/events", dependencies=[Depends(require_key)])
def ingest_event(item: Event):
    now = datetime.now(timezone.utc).isoformat()
    try:
        result = get_supabase().table("events").insert({
            "received_at": now,
            "severity": item.severity,
            "event_type": item.event_type,
            "message": item.message,
            "payload": item.payload,
        }).execute()
        inserted = result.data[0] if result.data else {}
        return {"accepted": True, "event_id": inserted.get("id"), "received_at": now}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Event storage failed: {exc}")


@app.get("/v1/latest", dependencies=[Depends(require_key)])
def latest():
    try:
        client = get_supabase()
        telemetry_result = (
            client.table("telemetry")
            .select("payload,received_at")
            .order("id", desc=True)
            .limit(1)
            .execute()
        )
        event_result = (
            client.table("events")
            .select("id,received_at,severity,event_type,message,payload")
            .order("id", desc=True)
            .limit(30)
            .execute()
        )
        row = telemetry_result.data[0] if telemetry_result.data else None
        return {
            "telemetry": row["payload"] if row else None,
            "received_at": row["received_at"] if row else None,
            "events": event_result.data or [],
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Telemetry query failed: {exc}")


@app.get("/v1/history", dependencies=[Depends(require_key)])
def history(limit: int = 100):
    limit = max(1, min(limit, 1000))
    try:
        result = (
            get_supabase().table("telemetry")
            .select("received_at,payload")
            .order("id", desc=True)
            .limit(limit)
            .execute()
        )
        return [
            {"received_at": row["received_at"], **(row.get("payload") or {})}
            for row in (result.data or [])
        ]
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Telemetry history query failed: {exc}")
