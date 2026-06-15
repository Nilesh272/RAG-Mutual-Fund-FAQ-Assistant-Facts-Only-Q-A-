"""Streamlit chat UI — calls ChatOrchestrator in-process (no separate API)."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from config.load_env import load_env
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


@st.cache_resource(show_spinner="Loading RAG pipeline…")
def get_orchestrator() -> ChatOrchestrator:
    load_env(PROJECT_ROOT)
    return ChatOrchestrator.from_config_files(PROJECT_ROOT)


def _ensure_thread() -> Thread:
    if "thread" not in st.session_state:
        st.session_state.thread = Thread.create()
    return st.session_state.thread


def _new_conversation() -> None:
    st.session_state.thread = Thread.create()


def _run_chat(user_message: str) -> None:
    orchestrator = get_orchestrator()
    thread = _ensure_thread()
    with st.spinner("Searching sources…"):
        orchestrator.handle_message(thread, user_message)


def main() -> None:
    st.set_page_config(
        page_title="Mutual Fund FAQ Assistant",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    orchestrator = get_orchestrator()

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
        try:
            health = orchestrator.health_status()
            if health["status"] == "ok":
                st.success(f"Index OK · {health['indexed_chunks']} chunks")
            else:
                st.warning(f"Index degraded · {health['indexed_chunks']} chunks")
            st.caption(f"Collection: `{health['collection']}`")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Health check failed: {exc}")

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
