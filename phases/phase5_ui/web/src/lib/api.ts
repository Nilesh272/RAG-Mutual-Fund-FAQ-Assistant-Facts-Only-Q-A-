import type { ChatResponse, HealthResponse, ThreadResponse } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      (body as { detail?: string }).detail ?? `Request failed (${res.status})`,
    );
  }
  return res.json() as Promise<T>;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

export function createThread(): Promise<ThreadResponse> {
  return request<ThreadResponse>("/api/threads", { method: "POST" });
}

export function sendChat(
  message: string,
  threadId?: string | null,
): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ thread_id: threadId ?? null, message }),
  });
}
