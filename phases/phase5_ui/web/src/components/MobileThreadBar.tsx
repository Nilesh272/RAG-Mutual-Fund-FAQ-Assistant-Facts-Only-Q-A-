interface MobileThreadBarProps {
  onNewConversation: () => void;
}

export function MobileThreadBar({ onNewConversation }: MobileThreadBarProps) {
  return (
    <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-3 lg:hidden">
      <span className="text-sm text-zinc-500">Current conversation</span>
      <button
        type="button"
        onClick={onNewConversation}
        className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-300 hover:bg-zinc-800"
      >
        New chat
      </button>
    </div>
  );
}
