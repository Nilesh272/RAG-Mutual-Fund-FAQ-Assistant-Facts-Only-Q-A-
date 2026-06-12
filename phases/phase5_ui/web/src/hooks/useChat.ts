"use client";

import { useCallback, useEffect, useState } from "react";
import { createThread, getHealth, sendChat } from "@/lib/api";
import type { ChatMessage, HealthResponse } from "@/lib/types";

const THREAD_KEY = "mf_faq_thread_id";

function newId(): string {
  return crypto.randomUUID();
}

export function useChat() {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [showWelcome, setShowWelcome] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem(THREAD_KEY);
    if (stored) setThreadId(stored);
    getHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
    createThread()
      .then((t) => {
        if (!stored) {
          setThreadId(t.thread_id);
          localStorage.setItem(THREAD_KEY, t.thread_id);
        }
      })
      .catch(() => setError("Could not connect to the API. Is the backend running?"));
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || loading) return;

      setShowWelcome(false);
      setError(null);
      setLoading(true);

      const userMsg: ChatMessage = {
        id: newId(),
        role: "user",
        content: trimmed,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);

      try {
        let activeThread = threadId ?? localStorage.getItem(THREAD_KEY);
        if (!activeThread) {
          const t = await createThread();
          activeThread = t.thread_id;
          setThreadId(activeThread);
          localStorage.setItem(THREAD_KEY, activeThread);
        }

        const res = await sendChat(trimmed, activeThread);
        setThreadId(res.thread_id);
        localStorage.setItem(THREAD_KEY, res.thread_id);

        const assistantMsg: ChatMessage = {
          id: newId(),
          role: "assistant",
          content: res.formatted_answer ?? res.answer,
          citation: res.citation,
          intent: res.intent,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Something went wrong.");
      } finally {
        setLoading(false);
      }
    },
    [threadId, loading],
  );

  const startNewConversation = useCallback(async () => {
    setMessages([]);
    setShowWelcome(true);
    setError(null);
    try {
      const t = await createThread();
      setThreadId(t.thread_id);
      localStorage.setItem(THREAD_KEY, t.thread_id);
    } catch {
      setError("Failed to start a new conversation.");
    }
  }, []);

  return {
    messages,
    loading,
    error,
    health,
    showWelcome,
    sendMessage,
    startNewConversation,
  };
}
