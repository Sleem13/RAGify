import json
import os
from typing import Any

import requests
import streamlit as st

st.set_page_config(
    page_title="RAGify Streamlit Demo",
    page_icon=":material/library_books:",
    layout="wide",
)

APP_TITLE = "RAGify Streamlit Demo"
DEFAULT_BACKEND_URL = os.getenv("RAGIFY_BACKEND_URL", "http://localhost:9999")


def get_backend_url() -> str:
    url = st.session_state.get("backend_url", "").strip()
    return (url or DEFAULT_BACKEND_URL).rstrip("/")


def get_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    api_key = st.session_state.get("api_key", "").strip()
    if api_key:
        headers["X-Api-Key"] = api_key
    return headers


@st.cache_data(ttl=10, max_entries=10, show_spinner=False)
def check_backend_status(url: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        response = requests.get(f"{url}/", timeout=6)
        if response.ok:
            return response.json(), None
        return None, f"Backend returned HTTP {response.status_code}"
    except requests.ConnectionError:
        return None, "Cannot connect to backend. Is it running?"
    except requests.Timeout:
        return None, "Backend took too long to respond."
    except requests.RequestException as exc:
        return None, f"Connection error: {exc}"


def upload_document(file_obj) -> tuple[dict[str, Any] | None, str | None]:
    if file_obj is None:
        return None, "Please choose a file to upload."

    files = {
        "file": (
            file_obj.name,
            file_obj.getvalue(),
            file_obj.type or "application/octet-stream",
        )
    }

    try:
        response = requests.post(
            f"{get_backend_url()}/upload",
            headers=get_headers(),
            files=files,
            timeout=180,
        )
    except requests.ConnectionError:
        return None, "Cannot connect to backend. Is it running?"
    except requests.Timeout:
        return None, "Upload timed out. The file may be too large."
    except requests.RequestException as exc:
        return None, f"Upload failed: {exc}"

    if response.ok:
        return response.json(), None
    try:
        detail = response.json().get("detail", response.text)
    except ValueError:
        detail = response.text
    return None, f"Upload failed: {detail}"


def list_indexed_files() -> tuple[list[dict[str, Any]], str | None]:
    try:
        response = requests.get(f"{get_backend_url()}/files", timeout=8)
    except requests.ConnectionError:
        return [], "Cannot connect to backend."
    except requests.RequestException as exc:
        return [], f"Could not load files: {exc}"

    if response.ok:
        payload = response.json()
        files = payload.get("files", {})
        return [{"name": name, **meta} for name, meta in files.items()], None
    return [], f"Could not load files: HTTP {response.status_code}"


def ask_question(
    message: str,
    history: list[dict[str, str]],
) -> tuple[str | None, str | None, list[dict[str, Any]], str | None]:
    try:
        response = requests.post(
            f"{get_backend_url()}/chat",
            headers=get_headers(),
            data={
                "message": message,
                "history": json.dumps(history),
            },
            timeout=120,
        )
    except requests.ConnectionError:
        return None, None, [], "Cannot connect to backend. Is it running?"
    except requests.Timeout:
        return None, None, [], "Request timed out. Please try again."
    except requests.RequestException as exc:
        return None, None, [], f"Request failed: {exc}"

    if response.ok:
        payload = response.json()
        return payload.get("response"), payload.get("action"), payload.get("sources", []), None

    try:
        detail = response.json().get("detail", response.text)
    except ValueError:
        detail = response.text
    return None, None, [], detail


def init_session_state() -> None:
    if "backend_url" not in st.session_state:
        st.session_state.backend_url = DEFAULT_BACKEND_URL
    if "api_key" not in st.session_state:
        st.session_state.api_key = ""
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hello! Upload a document or spreadsheet and I can help you explore it with RAGify.",
            }
        ]


init_session_state()

st.title(APP_TITLE)
st.caption("A lightweight Streamlit companion for the RAGify document intelligence experience.")

with st.sidebar:
    st.header("Connection")
    st.text_input("Backend URL", key="backend_url")
    st.text_input("API key", key="api_key", type="password")
    if st.button("Check backend"):
        check_backend_status.clear()

    status, error = check_backend_status(get_backend_url())
    if status:
        st.success(f"Backend healthy: {status.get('app', 'RAGify')}")
    else:
        st.warning(f"Backend unavailable: {error}")

    st.divider()
    st.markdown(
        "### What this demo shows\n"
        "- Upload PDFs, Word files, spreadsheets, or text\n"
        "- Ask questions grounded in indexed content\n"
        "- Preview dashboard-ready insights from Excel/CSV files"
    )

col1, col2 = st.columns([1.2, 0.8], gap="large")

with col1:
    st.subheader("Upload and index content")
    uploaded_file = st.file_uploader("Choose a document or spreadsheet", type=["pdf", "docx", "txt", "pptx", "png", "jpg", "jpeg", "xlsx", "xls", "csv", "json"])
    if st.button("Upload file") and uploaded_file is not None:
        with st.spinner("Processing your file..."):
            payload, error = upload_document(uploaded_file)
        if payload:
            st.success(payload.get("message", "File uploaded successfully."))
        if error:
            st.error(error)

    st.subheader("Indexed files")
    files, error = list_indexed_files()
    if error:
        st.info(error)
    elif files:
        for item in files:
            with st.container(border=True):
                st.write(f"**{item['name']}**")
                st.caption(f"Type: {item.get('type', 'unknown')} • Chunks: {item.get('chunks', 'n/a')}")
    else:
        st.info("No files have been indexed yet.")

with col2:
    st.subheader("Ask the assistant")
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            message_sources = message.get("sources", [])
            if message_sources:
                with st.expander(f"Sources ({len(message_sources)})"):
                    for source in message_sources:
                        st.markdown(f"**[Source {source['id']}] {source['title']}**")
                        st.caption(source["text"])

    prompt = st.chat_input("Ask about your uploaded documents", submit_mode="disable")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        history = [
            {"role": item["role"], "content": item["content"]}
            for item in st.session_state.messages[:-1]
        ]

        with st.spinner("Thinking..."):
            response, action, sources, error = ask_question(prompt, history)

        if error:
            reply = f"Sorry, something went wrong: {error}"
        elif response:
            reply = response
        else:
            reply = "The backend did not return a response."

        if action == "GENERATE_DASHBOARD":
            reply = f"{reply}\n\n🧭 Dashboard generation was requested. Open the analytics experience in the full app to view the visualization."

        st.session_state.messages.append(
            {"role": "assistant", "content": reply, "sources": sources}
        )
        with st.chat_message("assistant"):
            st.write(reply)
            if sources:
                with st.expander(f"Sources ({len(sources)})"):
                    for source in sources:
                        st.markdown(f"**[Source {source['id']}] {source['title']}**")
                        st.caption(source["text"])
        st.rerun()

st.markdown("---")
