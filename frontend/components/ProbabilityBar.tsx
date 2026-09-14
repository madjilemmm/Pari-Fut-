export function ProbabilityBar({
  homeLabel,
  drawLabel = "Nul",
  awayLabel,
  home,
  draw,
  away,
}: {
  homeLabel: string;
  drawLabel?: string;
  awayLabel: string;
  home: number;
  draw: number;
  away: number;
}) {
  const pct = (x: number) => `${(x * 100).toFixed(1)}%`;
  return (
    <div>
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-terminal-panel2">
        <div className="prob-bar bg-terminal-accent" style={{ width: pct(home) }} />
        <div className="prob-bar bg-terminal-muted/40" style={{ width: pct(draw) }} />
        <div className="prob-bar bg-terminal-accent2" style={{ width: pct(away) }} />
      </div>
      <div className="mt-2 grid grid-cols-3 text-center text-xs">
        <div>
          <div className="text-lg font-semibold text-terminal-accent">{pct(home)}</div>
          <div className="text-terminal-muted">{homeLabel}</div>
        </div>
        <div>
          <div className="text-lg font-semibold text-terminal-text">{pct(draw)}</div>
          <div className="text-terminal-muted">{drawLabel}</div>
        </div>
        <div>
          <div className="text-lg font-semibold text-terminal-accent2">{pct(away)}</div>
          <div className="text-terminal-muted">{awayLabel}</div>
        </div>
      </div>
    </div>
  );
}
