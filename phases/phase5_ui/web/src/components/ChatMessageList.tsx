"use client";

import { useEffect, useRef } from "react";
import type { ChatMessage as ChatMessageType } from "@/lib/types";
import { ChatMessage } from "./ChatMessage";
import { LoadingIndicator } from "./LoadingIndicator";

interface ChatMessageListProps {
  messages: ChatMessageType[];
  loading: boolean;
}

export function ChatMessageList({ messages, loading }: ChatMessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-1 py-2">
      {messages.map((msg) => (
        <ChatMessage key={msg.id} message={msg} />
      ))}
      {loading && <LoadingIndicator />}
      <div ref={bottomRef} />
    </div>
  );
}
