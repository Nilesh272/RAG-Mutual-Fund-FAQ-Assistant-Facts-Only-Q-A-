import type { HealthResponse } from "@/lib/types";

interface HeaderProps {
  health: HealthResponse | null;
}

export function Header({ health }: HeaderProps) {
  const isHealthy = health?.status === "ok" && (health?.indexed_chunks ?? 0) > 0;

  return (
    <header className="flex items-center justify-between border-b border-zinc-800 bg-zinc-950/80 px-6 py-4 backdrop-blur-md">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10 ring-1 ring-emerald-500/30">
          <span className="text-lg font-bold text-emerald-400">MF</span>
        </div>
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-zinc-50">
            Mutual Fund FAQ Assistant
          </h1>
          <p className="text-xs text-zinc-500">
            Five HDFC schemes · Groww pages only
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2 text-xs">
        <span
          className={`h-2 w-2 rounded-full ${isHealthy ? "bg-emerald-400" : "bg-amber-400"}`}
          aria-hidden
        />
        <span className="text-zinc-400">
          {health
            ? `${health.indexed_chunks} chunks indexed`
            : "API offline"}
        </span>
      </div>
    </header>
  );
}
