# Cloud control centre · Phase 1

This phase adds a read-only cloud telemetry path. It does not execute trades.

## Services

- `api/`: FastAPI ingestion API with bearer-key authentication and SQLite storage.
- `dashboard/`: Streamlit read-only dashboard.
- `../mt5/CloudBridge.mq5`: MT5 Expert Advisor that periodically posts account, position, quote, indicator and recent-bar telemetry.

## Run API locally

```bash
cd cloud/api
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Set a strong secret before starting:

PowerShell:
```powershell
$env:CLOUD_API_KEY="replace-with-a-long-random-secret"
uvicorn main:app --host 0.0.0.0 --port 8000
```

Linux/macOS:
```bash
export CLOUD_API_KEY="replace-with-a-long-random-secret"
uvicorn main:app --host 0.0.0.0 --port 8000
```

Health check: `GET /health`

## Run dashboard

```bash
cd cloud/dashboard
pip install -r requirements.txt
```

Set `CLOUD_API_URL` and `CLOUD_API_KEY`, then:

```bash
streamlit run app.py
```

Or enter the URL and key in the dashboard sidebar.

## MT5 setup

1. Compile `mt5/CloudBridge.mq5` in MetaEditor.
2. Attach it to a chart on the VPS.
3. Set `ApiBaseUrl` to the deployed API base URL, for example `https://your-service.example.com`.
4. Set `ApiKey` to the same secret as `CLOUD_API_KEY`.
5. In MT5: Tools → Options → Expert Advisors → enable "Allow WebRequest for listed URL" and add the API origin (without the endpoint path).
6. Keep AutoTrading enabled only if required by your terminal policy; this bridge contains no trade functions and cannot place orders.

## Data and security notes

- Never commit real API keys or broker credentials.
- Use HTTPS in deployment. Do not expose MT5 TCP socket port 9091 to the public internet.
- SQLite is suitable for a first single-instance test. For multi-instance or persistent production hosting, migrate to PostgreSQL and a persistent volume.
- The dashboard/API key is a personal MVP credential. Before multi-account or public use, add per-terminal identities, key rotation, rate limiting, audit retention and stronger secret management.
- Telemetry includes account identifiers and positions. Keep the API private and restrict dashboard access.
