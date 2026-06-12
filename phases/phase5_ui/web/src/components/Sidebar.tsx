interface SidebarProps {
  onNewConversation: () => void;
}

const SCHEMES = [
  "HDFC Large Cap Fund Direct Growth",
  "HDFC Mid Cap Fund Direct Growth",
  "HDFC Equity Fund Direct Growth",
  "HDFC Focused Fund Direct Growth",
  "HDFC ELSS Tax Saver Fund Direct Plan Growth",
];

export function Sidebar({ onNewConversation }: SidebarProps) {
  return (
    <aside className="hidden w-72 shrink-0 flex-col border-r border-zinc-800 bg-zinc-900/50 p-5 lg:flex">
      <button
        type="button"
        onClick={onNewConversation}
        className="mb-6 flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-emerald-500"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        New conversation
      </button>

      <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
        Schemes in scope
      </div>
      <ul className="space-y-2 text-sm text-zinc-400">
        {SCHEMES.map((name) => (
          <li
            key={name}
            className="rounded-lg border border-zinc-800/80 bg-zinc-950/50 px-3 py-2 leading-snug"
          >
            {name}
          </li>
        ))}
      </ul>

      <p className="mt-auto pt-6 text-xs leading-relaxed text-zinc-600">
        Answers are retrieved from indexed Groww scheme pages and refreshed daily at 9:15 AM IST.
      </p>
    </aside>
  );
}
