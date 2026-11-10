import os
import time
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="AI-Enhanced HFT Control", layout="wide")
st.title("AI-Enhanced HFT · Cloud Control Centre")
st.caption("Phase 1 · Read-only telemetry monitor. Trading controls are intentionally disabled.")

api_url = st.sidebar.text_input("API URL", os.getenv("CLOUD_API_URL", "http://localhost:8000")).rstrip("/")
api_key = st.sidebar.text_input("API key", os.getenv("CLOUD_API_KEY", ""), type="password")
refresh = st.sidebar.slider("Refresh interval (seconds)", 2, 30, 5)

if not api_key:
    st.info("Enter the API key in the sidebar, or configure CLOUD_API_KEY as an environment secret.")
    st.stop()

headers = {"Authorization": f"Bearer {api_key}"}
try:
    response = requests.get(f"{api_url}/v1/latest", headers=headers, timeout=5)
    response.raise_for_status()
    result = response.json()
except Exception as exc:
    st.error(f"API connection failed: {exc}")
    st.stop()

data = result.get("telemetry")
if not data:
    st.warning("API is online, but no MT5 telemetry has arrived yet.")
else:
    st.success(f"Latest telemetry received: {result.get('received_at', 'unknown')}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Balance", f"{data.get('balance', 0):,.2f}")
    c2.metric("Equity", f"{data.get('equity', 0):,.2f}")
    c3.metric("Open positions", data.get("positions_count", 0))
    c4.metric("Spread (points)", f"{data.get('spread_points') or 0:.1f}")

    left, right = st.columns(2)
    with left:
        st.subheader("Terminal")
        st.write({
            "Account": data.get("account_login"),
            "Broker server": data.get("server"),
            "Symbol": data.get("symbol"),
            "Timeframe": data.get("timeframe"),
            "EA status": data.get("ea_status"),
            "Terminal time": data.get("terminal_time"),
            "Bid": data.get("bid"),
            "Ask": data.get("ask"),
        })
        st.subheader("Indicators / features")
        st.json(data.get("indicators", {}))
    with right:
        st.subheader("Open positions")
        positions = data.get("positions", [])
        st.dataframe(pd.DataFrame(positions), use_container_width=True) if positions else st.info("No open positions reported.")

    st.subheader("Recent market bars")
    bars = data.get("bars", [])
    if bars:
        frame = pd.DataFrame(bars)
        st.dataframe(frame, use_container_width=True)
    else:
        st.info("No bar data in latest heartbeat.")

st.subheader("Recent system events")
events = result.get("events", [])
if events:
    event_frame = pd.DataFrame(events)
    st.dataframe(event_frame[["received_at", "severity", "event_type", "message"]], use_container_width=True)
else:
    st.caption("No events received.")

st.caption("This dashboard displays received telemetry only. It does not submit, modify, or close trades.")
time.sleep(refresh)
st.rerun()
