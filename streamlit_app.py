"""Streamlit chat UI — calls ChatOrchestrator in-process (no separate API)."""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from config.bootstrap_env import bootstrap_env, chroma_env_summary
from phases.phase4_api.orchestrator import ChatOrchestrator
from phases.phase4_api.session.models import Thread

PROJECT_ROOT = Path(__file__).resolve().parent

EXAMPLE_QUESTIONS = [
    "What is the expense ratio of HDFC Large Cap Fund?",
    "What is the minimum SIP for HDFC Mid Cap Fund?",
    "What is the ELSS lock-in period for HDFC ELSS?",
]

SCHEMES = [
    "HDFC Mid Cap Fund Direct Growth",
    "HDFC Equity Fund Direct Growth",
    "HDFC Focused Fund Direct Growth",
    "HDFC ELSS Tax Saver Fund Direct Plan Growth",
    "HDFC Large Cap Fund Direct Growth",
]


def _validate_chroma_env() -> list[str]:
    issues: list[str] = []
    env = chroma_env_summary()
    if not env["api_key_set"]:
        issues.append("Set `CHROMA_API_KEY` in Streamlit Secrets.")
    if not env["tenant"]:
        issues.append("Set `CHROMA_TENANT` in Streamlit Secrets.")
    if not env["database"]:
        issues.append("Set `CHROMA_DATABASE` in Streamlit Secrets (use `testDB`).")
    return issues


@st.cache_resource(show_spinner="Loading RAG pipeline…")
def get_orchestrator(chroma_database: str) -> ChatOrchestrator:
    bootstrap_env(PROJECT_ROOT)
    return ChatOrchestrator.from_config_files(PROJECT_ROOT)


def _ensure_thread() -> Thread:
    if "thread" not in st.session_state:
        st.session_state.thread = Thread.create()
    return st.session_state.thread


def _new_conversation() -> None:
    st.session_state.thread = Thread.create()


def _run_chat(user_message: str) -> None:
    bootstrap_env(PROJECT_ROOT)
    db = os.getenv("CHROMA_DATABASE", "")
    orchestrator = get_orchestrator(db)
    thread = _ensure_thread()
    with st.spinner("Searching sources…"):
        orchestrator.handle_message(thread, user_message)


def _render_index_status(orchestrator: ChatOrchestrator) -> None:
    env = chroma_env_summary()
    st.caption(
        f"Chroma DB: `{env['database'] or 'not set'}` · "
        f"tenant: `{env['tenant'][:8] + '…' if env['tenant'] else 'not set'}`"
    )

    try:
        health = orchestrator.health_status()
        chunks = health["indexed_chunks"]
        if health["status"] == "ok" and chunks > 0:
            st.success(f"Index OK · {chunks} chunks")
        elif chunks == 0:
            st.error("Index empty · 0 chunks")
            st.markdown(
                "The app connected to Chroma but found no indexed data. Check that:\n"
                "1. **`CHROMA_DATABASE`** in Streamlit Secrets is `testDB` "
                "(same as GitHub Actions ingest secrets)\n"
                "2. **GitHub Actions ingest** has run successfully "
                "(Actions → Daily Ingest Pipeline)\n"
                "3. After updating secrets, use **Manage app → Reboot** "
                "to clear the cached pipeline"
            )
        else:
            st.warning(f"Index degraded · {chunks} chunks")
        st.caption(f"Collection: `{health['collection']}`")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Health check failed: {exc}")


def main() -> None:
    st.set_page_config(
        page_title="Mutual Fund FAQ Assistant",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    bootstrap_env(PROJECT_ROOT)
    env_issues = _validate_chroma_env()
    if env_issues:
        st.error("Chroma Cloud is not configured for this deployment.")
        for issue in env_issues:
            st.markdown(f"- {issue}")
        st.markdown(
            "Add secrets in **Streamlit Cloud → Settings → Secrets**. "
            "See `.streamlit/secrets.toml.example` in the repo."
        )
        st.stop()

    db = os.getenv("CHROMA_DATABASE", "")
    orchestrator = get_orchestrator(db)

    with st.sidebar:
        st.title("HDFC MF FAQ")
        st.caption("Facts-only · Groww sources")

        if st.button("New conversation", use_container_width=True):
            _new_conversation()
            st.rerun()

        st.divider()
        st.subheader("Schemes in scope")
        for name in SCHEMES:
            st.markdown(f"- {name}")

        st.divider()
        _render_index_status(orchestrator)

    st.title("Mutual Fund FAQ Assistant")
    st.info("**Facts-only. No investment advice.**")

    thread = _ensure_thread()

    if not thread.messages:
        st.markdown(
            "Ask factual questions about five **HDFC mutual fund schemes**. "
            "Answers come from indexed Groww scheme pages only — expense ratio, "
            "exit load, minimum SIP, ELSS lock-in, benchmark, and more."
        )
        st.markdown("**Try asking**")
        cols = st.columns(1)
        for question in EXAMPLE_QUESTIONS:
            if cols[0].button(question, key=f"example-{question}", use_container_width=True):
                _run_chat(question)
                st.rerun()

    for message in thread.messages:
        with st.chat_message(message.role):
            st.markdown(message.content)
            if message.role == "assistant" and message.citation:
                st.markdown(f"[Source]({message.citation})")

    if prompt := st.chat_input("Ask about HDFC mutual fund schemes…"):
        _run_chat(prompt)
        st.rerun()


if __name__ == "__main__":
    main()
