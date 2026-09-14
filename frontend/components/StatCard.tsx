export function StatCard({
  label,
  value,
  sub,
  highlight = false,
}: {
  label: string;
  value: string;
  sub?: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-xl2 border p-5 ${
        highlight ? "border-terminal-accent/50 bg-terminal-accent/5" : "border-terminal-border bg-terminal-panel"
      }`}
    >
      <div className="text-xs uppercase tracking-wide text-terminal-muted mb-1">{label}</div>
      <div className={`text-3xl font-semibold ${highlight ? "text-terminal-accent" : "text-terminal-text"}`}>
        {value}
      </div>
      {sub && <div className="text-xs text-terminal-muted mt-1">{sub}</div>}
    </div>
  );
}
