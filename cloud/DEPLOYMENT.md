# Deployment guide — Phase 1

## Recommended topology

Deploy `cloud/api` as a persistent HTTPS web service and `cloud/dashboard` as a separate Streamlit service. The Windows VPS runs MT5 plus `mt5/CloudBridge.mq5`.

### API service

- Build context: repository root
- Dockerfile: `cloud/api/Dockerfile`
- Health-check path: `/health`
- Environment variables:
  - `CLOUD_API_KEY`: long random secret, at least 20 characters
  - `CLOUD_DB_PATH`: path on a persistent mounted volume, e.g. `/data/cloud_telemetry.sqlite3`
  - `PORT`: supplied by the hosting platform

Mount persistent storage at `/data` and set `CLOUD_DB_PATH=/data/cloud_telemetry.sqlite3`. Without persistent storage, SQLite telemetry can be lost when the service is replaced or restarted.

### Dashboard service

- App directory: `cloud/dashboard`
- Main file: `app.py`
- Install: `pip install -r requirements.txt`
- Secrets:
  - `CLOUD_API_URL`: API base URL
  - `CLOUD_API_KEY`: same secret as API service

Do not expose the API key in a public repository or browser-side JavaScript.

### MT5 VPS

1. Install MT5 and log in to the demo account.
2. Copy `mt5/CloudBridge.mq5` into `MQL5/Experts`.
3. Compile with MetaEditor.
4. Add the API origin to the MT5 WebRequest allow-list.
5. Attach the EA to the instrument chart.
6. Configure the HTTPS base URL and API key in EA inputs.
7. Confirm the dashboard receives heartbeats and account data.

## Phase 1 acceptance checks

- `GET /health` returns HTTP 200.
- Missing or incorrect bearer key is rejected.
- Correct key can post telemetry.
- Dashboard shows current account, quote, spread, positions and bars.
- MT5 Experts log shows successful telemetry posts.
- No order/trade methods exist in the bridge.

## Scope boundary

This release is read-only. It does not contain AI inference, order submission, modification, closure, or remote trading controls. Those are later milestones after telemetry and model feature parity are verified.
