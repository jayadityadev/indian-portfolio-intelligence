"""Iteration-1 Streamlit dashboard (placeholder).

Owner: Aryaman.

Thin client only — consumes the FastAPI JSON API (docs/IMPLEMENTATION_PLAN.md §15
and the `{ok, data/error}` envelope in §10.6). No business logic here.

This stub just pings /health so `make dev` boots end-to-end.
"""

import os

import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Portfolio Intelligence", layout="wide")
st.title("Indian Portfolio Intelligence")

st.markdown("_Iteration-1 dashboard — placeholder. See `docs/team/ARYAMAN.md`._")

try:
    r = requests.get(f"{API_URL}/health", timeout=5)
    if r.ok:
        st.success(f"API healthy — version {r.json()['version']}")
    else:
        st.error(f"API returned {r.status_code}")
except requests.ConnectionError:
    st.error(f"Cannot reach API at {API_URL}")
