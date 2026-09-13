"""
Pari Futé — Phase 1 API (Premier League only).

Explicitly NOT implemented yet: live fixtures, odds, injuries, lineups.
Any endpoint depending on those returns HTTP 501 with "Donnée indisponible"
rather than inventing a value.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.services import prediction_service

app = FastAPI(title="Pari Futé API", version="0.1.0-phase1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/matches")
def get_matches(limit: int = 20):
    return prediction_service.list_matches(limit=limit)


@app.get("/matches/{match_id}/prediction")
def get_prediction(match_id: str):
    try:
        return prediction_service.predict_match(match_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Match introuvable")
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=501, detail=f"Donnée indisponible: {e}")


@app.get("/matches/{match_id}/elo")
def get_elo(match_id: str):
    try:
        return prediction_service.elo_ratings_snapshot(match_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Match introuvable")


@app.get("/matches/{match_id}/odds")
def get_odds(match_id: str):
    raise HTTPException(status_code=501, detail="Donnée indisponible: aucun fournisseur de cotes configuré en Phase 1")


@app.get("/matches/{match_id}/injuries")
def get_injuries(match_id: str):
    raise HTTPException(status_code=501, detail="Donnée indisponible: aucune source de blessures configurée en Phase 1")


@app.get("/model/performance")
def get_model_performance():
    return {
        "model_version": "edge_v0.2_dixon_coles",
        "note": "Métriques issues du backtest walk-forward réel, voir docs/PHASE1_STATUS.md",
        "baseline_poisson_edge_v0_1": {
            "evaluation_period": "test_2023_2024_and_2024_2025",
            "log_loss": 1.1215,
            "brier_score": 0.5983,
            "accuracy": 0.5377,
        },
        "dixon_coles_edge_v0_2": "voir data/processed/backtest_dixon_coles_results.parquet (calcul en cours / dernier run)",
    }


@app.get("/health")
def health():
    return {"status": "ok", "phase": 1}
