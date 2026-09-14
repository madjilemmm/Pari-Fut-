import { getModelPerformance, getCalibration, ApiError } from "@/lib/api";
import { StatCard } from "@/components/StatCard";
import { ErrorCard } from "@/components/ErrorCard";

export const dynamic = "force-dynamic";

const METRIC_INFO: Record<string, string> = {
  "Log Loss": "Mesure la qualité des probabilités produites, pas seulement si la prédiction était correcte. Plus faible = meilleur.",
  "Brier Score": "Mesure l'écart entre les probabilités annoncées et les résultats réels. Plus faible = meilleur.",
  Accuracy: "Pourcentage de résultats correctement prédits. Utile, mais insuffisant seul pour juger un modèle probabiliste.",
};

function MetricLabel({ name }: { name: string }) {
  return (
    <span className="inline-flex items-center gap-1 text-xs text-terminal-muted">
      {name}
      <span className="group relative inline-block">
        <span className="cursor-help rounded-full border border-terminal-border w-4 h-4 inline-flex items-center justify-center text-[10px]">?</span>
        <span className="pointer-events-none absolute left-1/2 -translate-x-1/2 bottom-6 w-52 rounded-lg border border-terminal-border bg-terminal-panel2 p-2 text-[11px] text-terminal-text opacity-0 group-hover:opacity-100 transition z-10">
          {METRIC_INFO[name]}
        </span>
      </span>
    </span>
  );
}

function ComparisonBar({ label, poisson, dixonColes, lowerIsBetter = true }: { label: string; poisson: number; dixonColes: number; lowerIsBetter?: boolean }) {
  const max = Math.max(poisson, dixonColes) * 1.15;
  const poissonBest = lowerIsBetter ? poisson < dixonColes : poisson > dixonColes;
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <MetricLabel name={label} />
      </div>
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <span className="w-20 text-xs text-terminal-muted shrink-0">Poisson</span>
          <div className="flex-1 h-3 rounded-full bg-terminal-panel2 overflow-hidden">
            <div
              className={`h-full prob-bar ${poissonBest ? "bg-terminal-accent" : "bg-terminal-muted/50"}`}
              style={{ width: `${(poisson / max) * 100}%` }}
            />
          </div>
          <span className="w-16 text-xs text-right font-medium">{poisson.toFixed(4)}</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="w-20 text-xs text-terminal-muted shrink-0">Dixon-Coles</span>
          <div className="flex-1 h-3 rounded-full bg-terminal-panel2 overflow-hidden">
            <div
              className={`h-full prob-bar ${!poissonBest ? "bg-terminal-accent" : "bg-terminal-muted/50"}`}
              style={{ width: `${(dixonColes / max) * 100}%` }}
            />
          </div>
          <span className="w-16 text-xs text-right font-medium">{dixonColes.toFixed(4)}</span>
        </div>
      </div>
    </div>
  );
}

export default async function ModelPerformancePage() {
  let perf, calibration;
  try {
    [perf, calibration] = await Promise.all([getModelPerformance(), getCalibration()]);
  } catch (e) {
    return <ErrorCard message={e instanceof ApiError ? e.message : "Erreur inattendue."} />;
  }

  const poisson = perf.models.find((m) => m.model_version === "edge_v0.1_poisson");
  const dixonColes = perf.models.find((m) => m.model_version === "edge_v0.2_dixon_coles");

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-terminal-accent text-lg">Performance du modèle</h1>
        <p className="text-terminal-muted text-sm mt-1">{perf.note}</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Prédictions testées" value={String(perf.current_model.n_predictions)} />
        <StatCard label="Accuracy" value={`${(perf.current_model.accuracy * 100).toFixed(1)}%`} highlight />
        <StatCard label="Log Loss" value={perf.current_model.log_loss.toFixed(4)} />
        <StatCard label="Brier Score" value={perf.current_model.brier_score.toFixed(4)} />
      </div>

      <section className="rounded-xl2 border border-terminal-border bg-terminal-panel p-6">
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-sm uppercase tracking-wide text-terminal-muted">Modèle actuel</h2>
        </div>
        <div className="text-xl font-semibold">{perf.current_model.display_name}</div>
        <div className="text-xs text-terminal-muted">Version technique : {perf.current_model.version}</div>
        <div className="text-xs text-terminal-muted mt-2">{perf.current_model.evaluation_period}</div>
      </section>

      {poisson && dixonColes && (
        <section className="rounded-xl2 border border-terminal-border bg-terminal-panel p-6 space-y-6">
          <h2 className="text-sm uppercase tracking-wide text-terminal-muted">Poisson vs Dixon-Coles</h2>
          <ComparisonBar label="Log Loss" poisson={poisson.log_loss!} dixonColes={dixonColes.log_loss!} />
          <ComparisonBar label="Brier Score" poisson={poisson.brier_score!} dixonColes={dixonColes.brier_score!} />
          <ComparisonBar label="Accuracy" poisson={poisson.accuracy!} dixonColes={dixonColes.accuracy!} lowerIsBetter={false} />
          <p className="text-xs text-terminal-muted pt-2 border-t border-terminal-border">{dixonColes.status}</p>
        </section>
      )}

      <section className="rounded-xl2 border border-terminal-border bg-terminal-panel p-6 space-y-4">
        <h2 className="text-sm uppercase tracking-wide text-terminal-muted">Calibration</h2>
        <p className="text-sm text-terminal-muted italic">{calibration.note}</p>
        <div className="flex items-center gap-6">
          <div>
            <div className="text-2xl font-semibold">{calibration.expected_calibration_error}</div>
            <div className="text-xs text-terminal-muted">Expected Calibration Error (ECE)</div>
          </div>
          <div className="text-xs text-terminal-muted">
            Plus proche de 0 = mieux calibré. Basé sur {calibration.n_predictions} prédictions historiques.
          </div>
        </div>
        <div className="pt-2">
          <div className="text-xs text-terminal-muted mb-2">Probabilité annoncée → fréquence observée</div>
          <div className="space-y-1.5">
            {calibration.reliability_curve.map((pt, i) => (
              <div key={i} className="flex items-center gap-3 text-xs">
                <span className="w-16 text-terminal-muted">{(pt.predicted * 100).toFixed(0)}% annoncé</span>
                <div className="flex-1 h-2 rounded-full bg-terminal-panel2 overflow-hidden relative">
                  <div className="h-full bg-terminal-accent2/60 prob-bar" style={{ width: `${pt.predicted * 100}%` }} />
                  <div className="absolute top-0 h-full w-0.5 bg-terminal-accent" style={{ left: `${pt.observed * 100}%` }} />
                </div>
                <span className="w-16 text-right text-terminal-muted">{(pt.observed * 100).toFixed(0)}% réel</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
