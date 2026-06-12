const EXAMPLES = [
  "What is the expense ratio of HDFC Large Cap Fund?",
  "What is the minimum SIP for HDFC Mid Cap Fund?",
  "What is the ELSS lock-in period for HDFC ELSS?",
];

interface ExampleQuestionsProps {
  onSelect: (question: string) => void;
  disabled?: boolean;
}

export function ExampleQuestions({ onSelect, disabled }: ExampleQuestionsProps) {
  return (
    <div className="space-y-3">
      <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
        Try asking
      </p>
      <div className="flex flex-col gap-2">
        {EXAMPLES.map((q) => (
          <button
            key={q}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(q)}
            className="rounded-xl border border-zinc-800 bg-zinc-950/60 px-4 py-3 text-left text-sm text-zinc-300 transition hover:border-emerald-500/40 hover:bg-emerald-500/5 hover:text-zinc-100 disabled:opacity-50"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
