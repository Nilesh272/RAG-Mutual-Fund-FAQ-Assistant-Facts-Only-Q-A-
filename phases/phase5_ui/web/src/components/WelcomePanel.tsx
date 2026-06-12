export function WelcomePanel() {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
      <h2 className="mb-2 text-xl font-semibold text-zinc-100">
        Welcome
      </h2>
      <p className="text-sm leading-relaxed text-zinc-400">
        Ask factual questions about five HDFC mutual fund schemes. I answer using
        indexed Groww scheme pages only — expense ratio, exit load, minimum SIP,
        ELSS lock-in, benchmark, and more.
      </p>
    </div>
  );
}
