import json
import os
import time
from pathlib import Path
from typing import Any

import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent / ".env")

st.set_page_config(
    page_title="RAGify · House of Knowledge",
    page_icon=":material/account_balance:",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULT_BACKEND_URL = os.getenv("RAGIFY_BACKEND_URL", "http://localhost:9999")
DEFAULT_API_KEY = os.getenv("RAGIFY_API_KEY", "")
WELCOME_MESSAGE = (
    "Welcome to the House of Knowledge. Upload a source, then ask me to uncover "
    "facts, themes, comparisons, and evidence from your archive."
)
SUGGESTED_QUESTIONS = {
    "Summarize the collection": "Summarize the key ideas in the uploaded collection.",
    "Find the main concepts": "What are the main concepts across the uploaded sources?",
    "Compare the sources": "Compare the most important ideas in the uploaded sources.",
}
UPLOAD_STAGE_LABELS = {
    "queued": "Waiting to enter the archive",
    "extracting": "Reading the source",
    "chunking": "Organizing the text",
    "embedding": "Building the knowledge index",
    "finalizing": "Sealing the archive entry",
}


def get_backend_url() -> str:
    url = st.session_state.get("backend_url", "").strip()
    return (url or DEFAULT_BACKEND_URL).rstrip("/")


def get_headers() -> dict[str, str]:
    api_key = st.session_state.get("api_key", "").strip()
    return {"X-Api-Key": api_key} if api_key else {}


@st.cache_data(ttl=10, max_entries=10, show_spinner=False)
def check_backend_status(url: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        response = requests.get(f"{url}/", timeout=6)
        if response.ok:
            return response.json(), None
        return None, f"Backend returned HTTP {response.status_code}"
    except requests.ConnectionError:
        return None, "Cannot connect to the backend."
    except requests.Timeout:
        return None, "The backend took too long to respond."
    except requests.RequestException as exc:
        return None, f"Connection error: {exc}"


def upload_document(
    file_obj: Any,
    progress_status: Any,
) -> tuple[dict[str, Any] | None, str | None]:
    if file_obj is None:
        return None, "Choose a file before starting the upload."

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
            timeout=30,
        )
    except requests.ConnectionError:
        return None, "Cannot connect to the backend. Is it running?"
    except requests.Timeout:
        return None, "The upload timed out. The file may be too large."
    except requests.RequestException as exc:
        return None, f"Upload failed: {exc}"

    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        return None, f"Upload failed: {detail}"

    payload = response.json()
    job_id = payload.get("job_id")
    if not job_id:
        return payload, None

    previous_stage = ""
    for _ in range(600):
        try:
            job_response = requests.get(
                f"{get_backend_url()}/jobs/{job_id}",
                headers=get_headers(),
                timeout=10,
            )
            job_response.raise_for_status()
        except requests.RequestException as exc:
            return None, f"Could not check processing status: {exc}"

        job = job_response.json()
        stage = str(job.get("stage") or job.get("status") or "processing")
        progress = int(job.get("progress") or 0)
        if stage != previous_stage:
            stage_label = UPLOAD_STAGE_LABELS.get(stage, stage.replace("_", " ").title())
            progress_status.update(label=f"{stage_label} · {progress}%")
            progress_status.write(stage_label)
            previous_stage = stage

        if job.get("status") == "completed":
            return job.get("result"), None
        if job.get("status") == "failed":
            return None, job.get("error") or "Document processing failed."
        time.sleep(1)

    return None, "Document processing did not finish within 10 minutes."


def list_indexed_files() -> tuple[list[dict[str, Any]], str | None]:
    try:
        response = requests.get(
            f"{get_backend_url()}/files",
            headers=get_headers(),
            timeout=8,
        )
    except requests.ConnectionError:
        return [], "Cannot connect to the backend."
    except requests.RequestException as exc:
        return [], f"Could not load files: {exc}"

    if response.ok:
        payload = response.json()
        files = payload.get("files", {})
        return [{"name": name, **meta} for name, meta in files.items()], None
    try:
        detail = response.json().get("detail", response.text)
    except ValueError:
        detail = response.text
    suffix = f": {detail}" if detail else ""
    return [], f"Could not load files: HTTP {response.status_code}{suffix}"


def ask_question(
    message: str,
    history: list[dict[str, str]],
) -> tuple[str | None, str | None, list[dict[str, Any]], str | None]:
    try:
        response = requests.post(
            f"{get_backend_url()}/chat",
            headers=get_headers(),
            data={"message": message, "history": json.dumps(history)},
            timeout=120,
        )
    except requests.ConnectionError:
        return None, None, [], "Cannot connect to the backend. Is it running?"
    except requests.Timeout:
        return None, None, [], "The request timed out. Please try again."
    except requests.RequestException as exc:
        return None, None, [], f"Request failed: {exc}"

    if response.ok:
        payload = response.json()
        return (
            payload.get("response"),
            payload.get("action"),
            payload.get("sources", []),
            None,
        )

    try:
        detail = response.json().get("detail", response.text)
    except ValueError:
        detail = response.text
    return None, None, [], detail


def init_session_state() -> None:
    defaults = {
        "backend_url": DEFAULT_BACKEND_URL,
        "api_key": DEFAULT_API_KEY,
        "messages": [{"role": "assistant", "content": WELCOME_MESSAGE}],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_sources(sources: list[dict[str, Any]]) -> None:
    if not sources:
        return
    with st.expander(
        f"Evidence from {len(sources)} source{'s' if len(sources) != 1 else ''}",
        icon=":material/source:",
    ):
        for source in sources:
            title = source.get("title") or "Untitled source"
            source_id = source.get("id", "—")
            st.markdown(f"**Source {source_id} · {title}**")
            if source.get("page"):
                st.caption(f"Page {source['page']}")
            st.write(source.get("text") or "No preview is available.")


init_session_state()

backend_status, backend_error = check_backend_status(get_backend_url())
indexed_files, files_error = list_indexed_files()

with st.sidebar:
    st.markdown("## :material/account_balance: House of Knowledge")
    st.caption("A modern research chamber for your private collection.")

    st.subheader("Connection settings")
    st.text_input("Backend URL", key="backend_url", icon=":material/dns:")
    st.text_input(
        "API key",
        key="api_key",
        type="password",
        icon=":material/key:",
        help="Leave blank when local authentication is disabled.",
    )

    with st.container(horizontal=True, gap="small"):
        if st.button("Check", icon=":material/health_and_safety:"):
            check_backend_status.clear()
            st.rerun()
        if st.button("Clear chat", icon=":material/delete_sweep:"):
            st.session_state.messages = [
                {"role": "assistant", "content": WELCOME_MESSAGE}
            ]
            st.rerun()

    if backend_status:
        st.badge("Archive online", icon=":material/check_circle:", color="green")
        st.caption(f"Connected to {backend_status.get('app', 'RAGify')}.")
    else:
        st.badge("Archive offline", icon=":material/error:", color="red")
        st.caption(backend_error or "Backend unavailable.")

    with st.expander("Supported sources", icon=":material/description:"):
        st.caption("Documents: PDF, Word, PowerPoint, text, and JSON")
        st.caption("Data: Excel and CSV")
        st.caption("Images: PNG and JPEG")

with st.container(border=True):
    st.caption("RAGIFY RESEARCH CONSOLE")
    st.title("Preserve knowledge. Reveal insight.")
    st.write(
        "Build a searchable archive, consult it in natural language, and trace every "
        "answer back to its source."
    )
    with st.container(horizontal=True, gap="small"):
        if backend_status:
            st.badge("Connected", icon=":material/hub:", color="green")
        else:
            st.badge("Disconnected", icon=":material/hub:", color="red")
        st.badge(
            f"{len(indexed_files)} indexed source{'s' if len(indexed_files) != 1 else ''}",
            icon=":material/library_books:",
            color="blue",
        )
        st.badge("Grounded answers", icon=":material/verified:", color="violet")

metric_columns = st.columns(3, gap="medium")
metric_columns[0].metric("Indexed sources", len(indexed_files))
metric_columns[1].metric(
    "Available models",
    len(backend_status.get("loaded_models", [])) if backend_status else 0,
)
metric_columns[2].metric("Research pipeline", "Ready" if backend_status else "Offline")

archive_column, chat_column = st.columns([0.85, 1.35], gap="large")

with archive_column:
    with st.container(border=True):
        st.markdown("### :material/upload_file: Build the archive")
        st.caption("Add a source and RAGify will extract, organize, and index it.")
        uploaded_file = st.file_uploader(
            "Choose a source",
            type=[
                "pdf", "docx", "txt", "pptx", "png", "jpg", "jpeg",
                "xlsx", "xls", "csv", "json",
            ],
            help="Upload one source at a time. Processing continues through the backend job queue.",
        )
        upload_clicked = st.button(
            "Add to archive",
            type="primary",
            icon=":material/auto_stories:",
            disabled=uploaded_file is None or not backend_status,
        )
        if upload_clicked:
            upload_status = st.status("Sending source to the archive…", expanded=True)
            payload, upload_error = upload_document(uploaded_file, upload_status)
            if upload_error:
                upload_status.update(
                    label="The source could not be archived",
                    state="error",
                    expanded=True,
                )
                st.error(upload_error)
            else:
                upload_status.update(
                    label="Archive entry ready",
                    state="complete",
                    expanded=False,
                )
                st.toast(
                    (payload or {}).get("message", "Source indexed successfully."),
                    icon=":material/check_circle:",
                )
                time.sleep(0.5)
                st.rerun()

    st.markdown("### :material/book_2: The collection")
    if files_error:
        st.warning(files_error, icon=":material/cloud_off:")
    elif not indexed_files:
        with st.container(border=True):
            st.caption("Your archive is empty. Add the first source above.")
    else:
        collection = st.container(height=330, border=False)
        with collection:
            for item in indexed_files:
                with st.container(border=True):
                    st.markdown(f"**:material/description: {item['name']}**")
                    file_type = str(item.get("type", "unknown")).upper()
                    chunk_count = item.get("chunks", "—")
                    st.caption(f"{file_type} · {chunk_count} indexed passages")

with chat_column:
    st.markdown("### :material/forum: Consult the archive")
    st.caption("Ask a focused question. Each grounded answer includes its evidence.")

    conversation = st.container(height=520, border=True, autoscroll=True)
    with conversation:
        for message in st.session_state.messages:
            avatar = (
                ":material/person:"
                if message["role"] == "user"
                else ":material/auto_stories:"
            )
            with st.chat_message(message["role"], avatar=avatar):
                st.write(message["content"])
                render_sources(message.get("sources", []))

    suggested_prompt = None
    if len(st.session_state.messages) == 1:
        suggestion = st.pills(
            "Suggested questions",
            list(SUGGESTED_QUESTIONS),
            label_visibility="collapsed",
        )
        if suggestion:
            suggested_prompt = SUGGESTED_QUESTIONS[suggestion]

    typed_prompt = st.chat_input(
        "Ask about your uploaded sources",
        disabled=not backend_status or not indexed_files,
        submit_mode="disable",
    )
    prompt = suggested_prompt or typed_prompt

    if not indexed_files:
        st.caption(":material/info: Add a source to unlock archive questions.")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        history = [
            {"role": item["role"], "content": item["content"]}
            for item in st.session_state.messages[:-1]
        ]

        with st.status("Searching the archive…", type="compact"):
            response, action, sources, chat_error = ask_question(prompt, history)

        if chat_error:
            reply = f"I could not complete that search: {chat_error}"
        elif response:
            reply = response
        else:
            reply = "The archive did not return an answer. Try a more specific question."

        if action == "GENERATE_DASHBOARD":
            reply += (
                "\n\nDashboard generation was requested. Open the full analytics "
                "experience to view the visualization."
            )

        st.session_state.messages.append(
            {"role": "assistant", "content": reply, "sources": sources}
        )
        st.rerun()
