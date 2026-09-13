import Link from "next/link";
import "./globals.css";

export const metadata = {
  title: "Pari Futé — Terminal d'analyse football",
  description: "Analyse quantitative Premier League (Phase 1 MVP)",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className="min-h-screen bg-terminal-bg font-mono text-sm">
        <header className="border-b border-terminal-border px-6 py-4 flex items-center justify-between">
          <span className="text-terminal-accent font-bold tracking-wide">PARI FUTÉ</span>
          <nav className="flex gap-6 text-terminal-muted">
            <Link href="/" className="text-white">HOME</Link>
            <Link href="/model-performance">MODEL PERFORMANCE</Link>
          </nav>
        </header>
        <main className="px-6 py-8 max-w-5xl mx-auto">{children}</main>
      </body>
    </html>
  );
}
