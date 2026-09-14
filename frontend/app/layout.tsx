import Link from "next/link";
import "./globals.css";

export const metadata = {
  title: "Pari Futé — Football Intelligence",
  description: "Analyse prédictive du football fondée sur des modèles statistiques réels (Poisson, Dixon-Coles).",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className="min-h-screen bg-terminal-bg text-terminal-text">
        <header className="border-b border-terminal-border">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
            <div>
              <Link href="/" className="text-terminal-accent font-bold tracking-wide text-lg">
                PARI FUTÉ
              </Link>
              <div className="text-[11px] text-terminal-muted -mt-0.5">Football Intelligence</div>
            </div>
            <nav className="flex gap-5 text-xs sm:text-sm text-terminal-muted overflow-x-auto">
              <Link href="/" className="hover:text-terminal-text whitespace-nowrap">
                ACCUEIL
              </Link>
              <Link href="/archives" className="hover:text-terminal-text whitespace-nowrap">
                MATCHS
              </Link>
              <Link href="/model-performance" className="hover:text-terminal-text whitespace-nowrap">
                FIABILITÉ
              </Link>
              <Link href="/comment-ca-marche" className="hover:text-terminal-text whitespace-nowrap">
                COMMENT ÇA MARCHE
              </Link>
            </nav>
          </div>
        </header>
        <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8">{children}</main>
        <footer className="max-w-6xl mx-auto px-4 sm:px-6 py-8 text-[11px] text-terminal-muted border-t border-terminal-border mt-12">
          Pari Futé — les probabilités affichées proviennent exclusivement du moteur statistique
          (Poisson / Dixon-Coles), jamais d&apos;un modèle de langage. Une probabilité n&apos;est jamais une certitude.
        </footer>
      </body>
    </html>
  );
}
