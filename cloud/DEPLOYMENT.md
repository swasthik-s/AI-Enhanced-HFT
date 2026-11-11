# Deployment guide — Phase 1

## Recommended topology

Deploy `cloud/api` as an HTTPS web service and `cloud/dashboard` as a separate Streamlit service. The Windows VPS runs MT5 plus `mt5/CloudBridge.mq5`. Supabase PostgreSQL stores telemetry independently of Render.

### Supabase database setup

1. Open the Supabase project and go to **SQL Editor**.
2. Run the SQL in `cloud/api/supabase_schema.sql`.
3. Open **Project Settings → API Keys** (or the project's API keys page).
4. Create/copy a **secret key** for server-side use. Do not use the publishable key for this API's server-side database access.
5. Keep the secret key private. Add it only as a Render environment variable; never commit it or paste it into source code.

### API service (Render)

- Root directory: `cloud/api`
- Runtime: Python
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health-check path: `/health`

Environment variables:
- `CLOUD_API_KEY`: long random bearer secret shared with the dashboard and MT5 EA
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_SECRET_KEY`: Supabase server-side secret key (not the publishable key)
- `PORT`: supplied by Render

Remove the old `CLOUD_DB_PATH` variable. The API no longer uses SQLite. No Render disk is required for database persistence.

### Dashboard service

- App directory: `cloud/dashboard`
- Main file: `app.py`
- Install: `pip install -r requirements.txt`
- Secrets:
  - `CLOUD_API_URL`: API base URL
  - `CLOUD_API_KEY`: same bearer secret as the API service

Do not put the Supabase secret key in Streamlit secrets. The dashboard talks to Supabase only through FastAPI.

### MT5 VPS

1. Install MT5 and log in to the demo account.
2. Copy `mt5/CloudBridge.mq5` into `MQL5/Experts`.
3. Compile with MetaEditor.
4. Add the API origin to the MT5 WebRequest allow-list.
5. Attach the EA to the instrument chart.
6. Configure the HTTPS base URL and `CLOUD_API_KEY` in EA inputs.
7. Confirm the dashboard receives heartbeats and account data.

## Phase 1 acceptance checks

- `GET /health` returns HTTP 200 and reports database connected.
- Missing or incorrect bearer key is rejected.
- Correct key can post telemetry.
- Dashboard shows current account, quote, spread, positions and bars.
- MT5 Experts log shows successful telemetry posts.
- No order/trade methods exist in the bridge.

## Scope boundary

This release is read-only. It does not contain AI inference, order submission, modification, closure, or remote trading controls. Those are later milestones after telemetry and model feature parity are verified.
