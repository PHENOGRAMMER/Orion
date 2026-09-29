"""Python-first Streamlit interface for the Orion graph API."""

from __future__ import annotations

import os
import base64
import hashlib
import hmac
import json
import time
from typing import Any

import httpx
import streamlit as st


DEFAULT_API_URL = os.getenv("ORION_API_URL", "http://localhost:8000").rstrip("/")


def auth0_is_configured() -> bool:
    """Enable Auth0 when explicitly requested or when secrets are present."""
    env_value = os.getenv("ORION_AUTH0_ENABLED")
    if env_value is not None:
        return env_value.strip().lower() in {"1", "true", "yes", "on"}

    try:
        auth_config = st.secrets.get("auth", {})
        provider_config = auth_config.get("auth0", {})
        return bool(
            provider_config.get("client_id")
            and provider_config.get("client_secret")
            and provider_config.get("server_metadata_url")
        )
    except Exception:
        # Missing secrets are expected in local API-only development mode.
        return False


AUTH0_ENABLED = auth0_is_configured()

st.set_page_config(
    page_title="Orion Observatory",
    page_icon="O",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap');
    :root { --ink:#edf4f3; --muted:#91a7a4; --panel:#101b1c; --line:#243536; --cyan:#61d8d0; --amber:#f4b860; }
    .stApp { background: #081112; color: var(--ink); }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] { background: #0b1617; border-right: 1px solid var(--line); }
    .block-container { max-width: 1500px; padding-top: 2.5rem; }
    h1, h2, h3, p, label, button { font-family: 'DM Sans', sans-serif; }
    h1 { letter-spacing: -0.04em; font-size: 3rem !important; }
    code, .mono { font-family: 'Space Mono', monospace; }
    .eyebrow { color: var(--cyan); font: 700 .72rem 'Space Mono', monospace; letter-spacing: .16em; text-transform: uppercase; }
    .lede { color: var(--muted); font-size: 1.05rem; max-width: 680px; line-height: 1.6; }
    .metric-card { background: linear-gradient(135deg, #122324, #0d191a); border: 1px solid var(--line); padding: 1rem 1.1rem; border-radius: 8px; min-height: 110px; }
    .metric-card:hover { border-color: var(--cyan); }
    .metric-label { color: var(--muted); font-size: .78rem; text-transform: uppercase; letter-spacing: .12em; }
    .metric-value { color: var(--ink); font-size: 2rem; font-weight: 700; margin-top: .3rem; }
    .status { color: var(--cyan); font: .78rem 'Space Mono', monospace; }
    section[data-testid="stSidebar"] .stMarkdown h2 { font-size: 1rem; }
    div[data-testid="stForm"] { border: 1px solid var(--line); background: var(--panel); border-radius: 8px; padding: 1rem; }
    .stButton button, .stFormSubmitButton button { border-radius: 6px; border: 1px solid #3f7775; background: #173536; color: var(--ink); }
    .stButton button:hover, .stFormSubmitButton button:hover { border-color: var(--cyan); color: var(--cyan); }
    .metric-button button { min-height: 110px; text-align: left; }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_auth_boundary() -> None:
    """Render Auth0 login/logout while preserving the local dev bypass."""
    if not AUTH0_ENABLED:
        return

    if not st.user.is_logged_in:
        st.title("Sign in to Orion")
        st.caption("Use your Auth0 account. Google and GitHub are available from the Auth0 login screen.")
        if st.button("Continue with Auth0", type="primary", width="stretch"):
            st.login("auth0")
        st.stop()

    display_name = st.user.get("name") or st.user.get("email") or "signed-in user"
    email = st.user.get("email") or ""
    picture = st.user.get("picture")
    subject = str(st.user.get("sub") or "")
    provider_key = subject.split("|", 1)[0].lower()
    provider_labels = {
        "google-oauth2": "Google",
        "github": "GitHub",
        "auth0": "Auth0",
    }
    provider = provider_labels.get(provider_key, provider_key or "Auth0")

    with st.sidebar:
        identity_columns = st.columns([1, 4])
        with identity_columns[0]:
            if picture:
                st.image(picture, width=42)
            else:
                st.markdown("### ◉")
        with identity_columns[1]:
            st.markdown(f"**{display_name}**")
            if email:
                st.caption(email)
            st.caption(f"Signed in with {provider}")
        if st.button("Sign out", width="stretch"):
            st.logout()


render_auth_boundary()


def api_get(path: str, **params: Any) -> dict[str, Any]:
    response = httpx.get(f"{api_url()}{path}", params=params or None, headers=api_headers(), timeout=15)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = httpx.post(f"{api_url()}{path}", json=payload, headers=api_headers(), timeout=60)
    response.raise_for_status()
    return response.json()


def api_url() -> str:
    """Return the per-user API URL, preserving sidebar changes across reruns."""
    return st.session_state.get("api_url", DEFAULT_API_URL).rstrip("/")


def api_error_message(exc: httpx.HTTPError) -> str:
    """Turn common API failures into useful user-facing guidance."""
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        detail = exc.response.text
        if status == 401:
            if AUTH0_ENABLED:
                return "Authentication failed. Sign in again or verify the Orion/Auth0 bridge configuration."
            return "Authentication failed. Enter a valid Orion API key."
        if status == 403:
            return "This action requires an admin API key."
        if status == 409:
            return "Another scan is already running. Check its status and try again later."
        if status == 503:
            return "Orion is not ready yet. Confirm the backend has a loaded graph and try again."
        return f"Orion returned HTTP {status}: {detail}"
    if isinstance(exc, httpx.TimeoutException):
        return "The Orion API timed out. Large repositories may take longer to scan."
    return f"Could not reach Orion at {api_url()}: {exc}"


def api_headers() -> dict[str, str]:
    key = st.session_state.get("api_key", "").strip()
    headers = {"X-API-Key": key} if key else {}
    headers.update(identity_bridge_headers())
    return headers


def identity_bridge_headers() -> dict[str, str]:
    """Sign verified Auth0 claims before the Streamlit server calls FastAPI."""
    if not AUTH0_ENABLED or not st.user.is_logged_in:
        return {}

    try:
        secret = str(st.secrets["orion"]["identity_bridge_secret"]).strip()
    except (KeyError, TypeError, FileNotFoundError):
        return {}

    identity = {
        "sub": str(st.user.get("sub") or ""),
        "name": st.user.get("name"),
        "email": st.user.get("email"),
        "picture": st.user.get("picture"),
        "iat": int(time.time()),
    }
    raw = json.dumps(identity, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    signature = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    return {
        "X-Orion-Identity": encoded,
        "X-Orion-Identity-Signature": signature,
    }


def node_name(item: dict[str, Any]) -> str:
    return item.get("qualified_name") or item.get("name") or item.get("id") or "unknown"


def choose_symbol(symbol: str) -> None:
    st.session_state["selected_symbol"] = symbol
    st.session_state["active_view"] = "symbol"


def relation_list(title: str, items: list[dict[str, Any]], direction: str) -> None:
    st.markdown(f"**{title}** · {len(items)}")
    if not items:
        st.caption(f"No direct {direction}.")
        return
    for index, item in enumerate(items):
        name = node_name(item)
        if st.button(name, key=f"{direction}-{index}-{name}", width="stretch"):
            choose_symbol(name)
            st.rerun()


st.markdown('<div class="eyebrow">ORION / OBSERVATORY</div>', unsafe_allow_html=True)
st.title("See how your code moves.")
st.markdown(
    '<p class="lede">A Python-first control room for the knowledge graph: inspect relationships, ask grounded questions, and keep the system map in view.</p>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## Connection")
    st.session_state.setdefault("api_url", DEFAULT_API_URL)
    st.session_state.setdefault("api_key", "")
    st.text_input("Orion API", key="api_url")
    if not AUTH0_ENABLED:
        st.text_input("API key", type="password", key="api_key")
    else:
        st.caption("Requests are associated with your Auth0 account.")
    st.caption("The bundled FastAPI UI remains available at /app.")
    refresh = st.button("Refresh graph", width="stretch")

    st.markdown("## Scan a repository")
    with st.form("scan_form"):
        scan_path = st.text_input(
            "Python repository path",
            placeholder=r"C:\work\my-python-repo",
            help="The path must be inside the backend ALLOWED_ROOTS configuration.",
        )
        scan_submitted = st.form_submit_button("Scan repository", width="stretch")

    if scan_submitted:
        if not scan_path.strip():
            st.warning("Enter a repository path first.")
        else:
            try:
                scan = api_post("/graph/scan", {"path": scan_path.strip()})
                st.session_state["scan_job_id"] = scan["job_id"]
                st.session_state["scan_message"] = scan.get("message", "Scan queued")
                st.rerun()
            except httpx.HTTPError as exc:
                st.error(api_error_message(exc))

    scan_job_id = st.session_state.get("scan_job_id")
    if scan_job_id:
        try:
            scan_status = api_get(f"/graph/scan/{scan_job_id}")
            scan_state = scan_status.get("status", "unknown")
            if scan_state == "done":
                st.success(scan_status.get("message", "Scan complete."))
                st.session_state.pop("scan_job_id", None)
            elif scan_state == "error":
                st.error(scan_status.get("message", "The scan failed."))
                st.session_state.pop("scan_job_id", None)
            else:
                st.info(f"Scan {scan_state}: {scan_status.get('message', 'working...')}")
                if st.button("Check scan status", width="stretch"):
                    st.rerun()
        except httpx.HTTPError as exc:
            st.error(api_error_message(exc))

    if AUTH0_ENABLED and st.user.is_logged_in:
        st.markdown("## Scan history")
        try:
            history = api_get("/graph/history").get("scans", [])
            if not history:
                st.caption("No saved scans for this account yet.")
            for scan in history:
                label = f"{scan.get('status', 'unknown').title()} · {scan.get('project_path', 'unknown')}"
                if scan.get("status") == "done":
                    if st.button(label, key=f"activate-{scan['job_id']}", width="stretch"):
                        api_post(f"/graph/history/{scan['job_id']}/activate", {})
                        st.session_state["active_view"] = "symbol"
                        st.rerun()
                else:
                    st.caption(label)
        except httpx.HTTPError as exc:
            st.error(api_error_message(exc))

try:
    stats = api_get("/graph/stats")
    st.markdown('<div class="status">● LIVE GRAPH SNAPSHOT</div>', unsafe_allow_html=True)
except httpx.HTTPError as exc:
    st.error(api_error_message(exc))
    st.stop()

if refresh:
    st.rerun()

by_edges = stats.get("by_edge_type", {})
metric_views = (
    ("nodes", "Nodes", stats.get("nodes", 0)),
    ("edges", "Edges", stats.get("edges", 0)),
    ("calls", "Calls", by_edges.get("calls", 0)),
    ("symbols", "Searchable symbols", stats.get("symbols_indexed", 0)),
)
cols = st.columns(4)
for column, (view, label, value) in zip(cols, metric_views):
    with column:
        st.markdown('<div class="metric-button">', unsafe_allow_html=True)
        if st.button(f"{label}\n{value:,}", key=f"metric-{view}", width="stretch"):
            st.session_state["active_view"] = view
        st.markdown('</div>', unsafe_allow_html=True)

active_view = st.session_state.get("active_view", "symbol")
if active_view in {"nodes", "edges", "calls", "symbols"}:
    titles = {
        "nodes": "Node inventory",
        "edges": "Edge inventory",
        "calls": "Call inventory",
        "symbols": "Searchable symbol inventory",
    }
    st.subheader(titles[active_view])
    try:
        export = api_get("/export", download="true")
        nodes = export.get("nodes", {})
        edges = export.get("edges", [])
        if active_view == "nodes":
            rows = [{"id": node_id, **value} for node_id, value in nodes.items()]
        elif active_view in {"edges", "calls"}:
            rows = [edge for edge in edges if active_view == "edges" or edge.get("type") == "calls"]
        else:
            rows = [
                {"symbol": node_id.removeprefix("symbol:"), "type": value.get("type"), "file": value.get("file")}
                for node_id, value in nodes.items()
                if node_id.startswith("symbol:")
            ]
        st.dataframe(rows, hide_index=True, width="stretch", height=420)
    except httpx.HTTPError as exc:
        st.error(api_error_message(exc))
    st.caption("Use symbol search below to open a focused relationship detail view.")

st.space("medium")
left, right = st.columns([1.05, 1.4], gap="large")

with left:
    st.subheader("Find a symbol")
    with st.form("search_form"):
        query = st.text_input("Search", placeholder="e.g. scan_project")
        submitted = st.form_submit_button("Search", width="stretch")
    if submitted and query.strip():
        try:
            results = api_get("/graph/search", q=query.strip(), limit=20).get("results", [])
            st.session_state["results"] = results
        except httpx.HTTPError as exc:
            st.error(api_error_message(exc))

    results = st.session_state.get("results", [])
    if results:
        labels = [item.get("qualified_name", item.get("name", "unknown")) for item in results]
        selected_default = st.session_state.get("selected_symbol", labels[0])
        selected_index = labels.index(selected_default) if selected_default in labels else 0
        selected = st.selectbox("Results", labels, index=selected_index)
        st.session_state["selected_symbol"] = selected
        selected_item = results[labels.index(selected)]
        st.caption(f"{selected_item.get('type', 'symbol')} · {selected_item.get('file', 'unknown file')}:{selected_item.get('line', '?')}")
    else:
        selected = ""
        st.info("Search the graph to inspect a symbol's neighborhood.")

with right:
    st.subheader("Relationship details")
    if selected:
        try:
            details = api_get(f"/graph/symbol/{selected}")
            symbol = details.get("symbol") or {}
            with st.container(border=True):
                st.markdown(f"**{node_name(symbol)}**")
                st.caption(f"{symbol.get('type', 'symbol')} · {symbol.get('file', 'unknown file')}:{symbol.get('line', '?')}")
                caller_col, callee_col = st.columns(2)
                with caller_col:
                    relation_list("Callers", details.get("callers", []), "caller")
                with callee_col:
                    relation_list("Callees", details.get("callees", []), "callee")
        except httpx.HTTPError as exc:
            st.error(api_error_message(exc))
    else:
        st.markdown("Select a symbol to bring its local graph into focus.")

st.space("medium")
st.subheader("Ask Orion")
question_col, action_col = st.columns([4, 1])
with question_col:
    question = st.text_input("Question", placeholder="What calls this symbol, and what could a change affect?", label_visibility="collapsed")
with action_col:
    ask = st.button("Ask", width="stretch", disabled=not bool(selected and question.strip()))

if ask and selected:
    try:
        answer = api_post("/llm/ask", {"question": question, "focal_symbol": selected})
        st.markdown(answer.get("answer", "No answer returned."))
        st.caption(f"{answer.get('device', 'unknown')} · {answer.get('latency_ms', 0)} ms")
    except httpx.HTTPError as exc:
        st.error(api_error_message(exc))

st.caption(f"Project: {stats.get('project_path') or 'No project loaded'}")
