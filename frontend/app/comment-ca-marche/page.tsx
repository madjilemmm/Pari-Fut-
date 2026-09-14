const STEPS = [
  "Nous collectons les résultats historiques réels (football-data.co.uk).",
  "Nous estimons la force offensive et défensive de chaque équipe (modèle Dixon-Coles).",
  "Le modèle estime le nombre de buts attendu (xG) pour chaque équipe.",
  "Des milliers de scénarios de score sont évalués à partir de ces xG.",
  "Ils sont convertis en probabilités : victoire, nul, défaite, plus de 2,5 buts, etc.",
  "Les performances sont vérifiées sur des matchs que le modèle n'a jamais vus (walk-forward backtest), jamais sur les données d'entraînement.",
];

export default function HowItWorksPage() {
  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div>
        <h1 className="text-terminal-accent text-lg">Comment ça marche ?</h1>
        <p className="text-terminal-muted text-sm mt-1">
          Pari Futé n&apos;est pas un pronostic généré par une intelligence artificielle conversationnelle. C&apos;est
          un système quantitatif : chaque probabilité provient d&apos;un modèle statistique entraîné et validé sur des
          données réelles.
        </p>
      </div>

      <ol className="space-y-4">
        {STEPS.map((step, i) => (
          <li key={i} className="flex gap-4 rounded-xl2 border border-terminal-border bg-terminal-panel p-4">
            <span className="shrink-0 w-7 h-7 rounded-full bg-terminal-accent/10 text-terminal-accent flex items-center justify-center text-sm font-semibold">
              {i + 1}
            </span>
            <span className="text-sm">{step}</span>
          </li>
        ))}
      </ol>

      <div className="rounded-xl2 border border-terminal-accent/30 bg-terminal-accent/5 p-5 text-center">
        <p className="font-medium">Une probabilité n&apos;est jamais une certitude.</p>
      </div>

      <div className="text-xs text-terminal-muted space-y-2">
        <p>
          Le modèle actuel (Dixon-Coles) est comparé objectivement à une baseline plus simple (Poisson) sur des
          matchs jamais utilisés pour l&apos;entraîner. Il n&apos;est conservé comme modèle par défaut que parce
          qu&apos;il obtient un meilleur Log Loss et Brier Score hors échantillon — voir la page{" "}
          <a href="/model-performance" className="text-terminal-accent hover:underline">
            Performance du modèle
          </a>
          .
        </p>
        <p>
          Quand une donnée n&apos;est pas disponible (cotes de marché, compositions, blessures), l&apos;application
          affiche « Donnée indisponible » plutôt que d&apos;inventer une valeur.
        </p>
      </div>
    </div>
  );
}
