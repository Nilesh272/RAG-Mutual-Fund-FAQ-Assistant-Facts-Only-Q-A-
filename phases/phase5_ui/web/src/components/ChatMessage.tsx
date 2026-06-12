import type { ReactNode } from "react";
import type { ChatMessage as ChatMessageType } from "@/lib/types";

function linkify(text: string): ReactNode[] {
  const parts = text.split(/(https?:\/\/[^\s)>\]]+)/g);
  return parts.map((part, i) =>
    /^https?:\/\//.test(part) ? (
      <a
        key={i}
        href={part}
        target="_blank"
        rel="noopener noreferrer"
        className="break-all text-emerald-400 underline underline-offset-2 hover:text-emerald-300"
      >
        {part}
      </a>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

interface ChatMessageProps {
  message: ChatMessageType;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "bg-emerald-600/20 text-zinc-100 ring-1 ring-emerald-500/20"
            : "bg-zinc-800/80 text-zinc-200 ring-1 ring-zinc-700/50"
        }`}
      >
        <div className="whitespace-pre-wrap">{linkify(message.content)}</div>
        {!isUser && message.intent && (
          <div className="mt-2 text-[10px] uppercase tracking-wider text-zinc-500">
            {message.intent.replace(/_/g, " ")}
          </div>
        )}
      </div>
    </div>
  );
}
