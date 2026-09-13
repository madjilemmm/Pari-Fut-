const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const dynamic = "force-dynamic";

export default async function ModelPerformancePage() {
  const res = await fetch(`${API_BASE}/model/performance`, { cache: "no-store" });
  const data = await res.json();

  return (
    <div className="space-y-4">
      <h1 className="text-terminal-accent text-lg">Model Performance</h1>
      <p className="text-terminal-muted">{data.note}</p>
      {data.models.map((m: any) => (
        <div key={m.model_version} className="border border-terminal-border rounded-lg p-4 bg-terminal-panel">
          <h2 className="mb-2">{m.model_version}</h2>
          <div className="text-terminal-muted text-xs grid grid-cols-2 gap-2">
            {m.evaluation_period && <div>Période: {m.evaluation_period}</div>}
            {m.n_predictions && <div>N prédictions: {m.n_predictions}</div>}
            {m.log_loss !== undefined && <div>Log Loss: {m.log_loss}</div>}
            {m.brier_score !== undefined && <div>Brier Score: {m.brier_score}</div>}
            {m.accuracy !== undefined && <div>Accuracy: {m.accuracy}</div>}
            {m.expected_calibration_error !== undefined && <div>ECE: {m.expected_calibration_error}</div>}
          </div>
          {m.status && <p className="mt-2 text-xs">{m.status}</p>}
        </div>
      ))}
    </div>
  );
}
