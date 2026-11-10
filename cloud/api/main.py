import json
import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

DB_PATH = os.getenv("CLOUD_DB_PATH", "cloud_telemetry.sqlite3")
API_KEY = os.getenv("CLOUD_API_KEY", "")
app = FastAPI(title="AI-Enhanced-HFT Cloud API", version="0.1.0")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            received_at TEXT NOT NULL,
            account_login TEXT,
            server TEXT,
            symbol TEXT,
            timeframe TEXT,
            payload TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            received_at TEXT NOT NULL,
            severity TEXT NOT NULL,
            event_type TEXT NOT NULL,
            message TEXT NOT NULL,
            payload TEXT NOT NULL
        )""")


@app.on_event("startup")
def startup():
    init_db()


def require_key(authorization: str | None = Header(default=None)):
    if not API_KEY:
        raise HTTPException(status_code=503, detail="Cloud API key is not configured")
    expected = f"Bearer {API_KEY}"
    if authorization != expected:
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
    return {"status": "ok", "service": "ai-enhanced-hft-api", "time": datetime.now(timezone.utc).isoformat()}


@app.post("/v1/telemetry", dependencies=[Depends(require_key)])
def ingest_telemetry(item: Telemetry):
    now = datetime.now(timezone.utc).isoformat()
    payload = item.model_dump()
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO telemetry(received_at,account_login,server,symbol,timeframe,payload) VALUES(?,?,?,?,?,?)",
            (now, item.account_login, item.server, item.symbol, item.timeframe, json.dumps(payload)),
        )
    return {"accepted": True, "telemetry_id": cur.lastrowid, "received_at": now}


@app.post("/v1/events", dependencies=[Depends(require_key)])
def ingest_event(item: Event):
    now = datetime.now(timezone.utc).isoformat()
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO events(received_at,severity,event_type,message,payload) VALUES(?,?,?,?,?)",
            (now, item.severity, item.event_type, item.message, json.dumps(item.payload)),
        )
    return {"accepted": True, "event_id": cur.lastrowid, "received_at": now}


@app.get("/v1/latest", dependencies=[Depends(require_key)])
def latest():
    with db() as conn:
        row = conn.execute("SELECT * FROM telemetry ORDER BY id DESC LIMIT 1").fetchone()
        events = conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT 30").fetchall()
    if row is None:
        return {"telemetry": None, "events": []}
    return {
        "telemetry": json.loads(row["payload"]),
        "received_at": row["received_at"],
        "events": [dict(e) for e in events],
    }


@app.get("/v1/history", dependencies=[Depends(require_key)])
def history(limit: int = 100):
    limit = max(1, min(limit, 1000))
    with db() as conn:
        rows = conn.execute("SELECT received_at,payload FROM telemetry ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [{"received_at": r["received_at"], **json.loads(r["payload"])} for r in rows]
