export function ErrorCard({ message }: { message: string }) {
  return (
    <div className="rounded-xl2 border border-terminal-danger/30 bg-terminal-danger/5 p-6 text-center">
      <p className="text-terminal-text mb-1">Impossible de récupérer l&apos;analyse pour le moment.</p>
      <p className="text-terminal-muted text-xs mb-4">{message}</p>
      <a
        href="."
        className="inline-block rounded-lg border border-terminal-border px-4 py-2 text-sm text-terminal-text hover:border-terminal-accent transition"
      >
        RÉESSAYER
      </a>
    </div>
  );
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-xl2 border border-dashed border-terminal-border p-6 text-center">
      <p className="text-terminal-text mb-1">{title}</p>
      <p className="text-terminal-muted text-xs">{body}</p>
    </div>
  );
}

export function Skeleton({ className = "h-24" }: { className?: string }) {
  return <div className={`skeleton rounded-xl2 ${className}`} />;
}
