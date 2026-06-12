"use client";

import { useChat } from "@/hooks/useChat";
import { ChatInput } from "./ChatInput";
import { ChatMessageList } from "./ChatMessageList";
import { DisclaimerBanner } from "./DisclaimerBanner";
import { ErrorAlert } from "./ErrorAlert";
import { ExampleQuestions } from "./ExampleQuestions";
import { Header } from "./Header";
import { MobileThreadBar } from "./MobileThreadBar";
import { Sidebar } from "./Sidebar";
import { WelcomePanel } from "./WelcomePanel";

export function ChatApp() {
  const {
    messages,
    loading,
    error,
    health,
    showWelcome,
    sendMessage,
    startNewConversation,
  } = useChat();

  return (
    <div className="flex h-screen flex-col bg-zinc-950 text-zinc-100">
      <Header health={health} />
      <div className="flex min-h-0 flex-1">
        <Sidebar onNewConversation={startNewConversation} />
        <main className="flex min-h-0 flex-1 flex-col">
          <MobileThreadBar onNewConversation={startNewConversation} />
          <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden p-4 md:p-6">
            <DisclaimerBanner />
            <ErrorAlert message={error} />
            {showWelcome && messages.length === 0 && (
              <div className="space-y-4">
                <WelcomePanel />
                <ExampleQuestions onSelect={sendMessage} disabled={loading} />
              </div>
            )}
            <ChatMessageList messages={messages} loading={loading} />
          </div>
          <ChatInput onSend={sendMessage} disabled={loading} />
        </main>
      </div>
    </div>
  );
}
