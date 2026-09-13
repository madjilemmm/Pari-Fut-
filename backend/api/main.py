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


@app.get("/matches/{match_id}/simulations")
def get_simulations(match_id: str):
    try:
        return prediction_service.simulate_match(match_id)
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
        "note": "Métriques issues de backtests walk-forward réels sur données PL réelles. Voir docs/PHASE1_STATUS.md.",
        "models": [
            {
                "model_version": "edge_v0.1_poisson",
                "evaluation_period": "test_2022_2023_to_2024_2025 (weekly walk-forward refit)",
                "n_predictions": 1140,
                "log_loss": 1.1215,
                "brier_score": 0.5983,
                "accuracy": 0.5377,
                "status": "baseline",
            },
            {
                "model_version": "edge_v0.1_poisson_isotonic_calibrated",
                "evaluation_period": "held-out 30% slice of the backtest above",
                "n_predictions": 342,
                "log_loss": 0.6297,
                "brier_score": 0.2202,
                "expected_calibration_error": 0.0740,
                "status": "calibration improves Brier/LogLoss vs raw on the same held-out slice (raw: LogLoss=0.6304, Brier=0.2205); see ml/evaluation/calibration.py",
            },
            {
                "model_version": "edge_v0.2_dixon_coles",
                "status": "validation-only so far — xi=0.005 selected via grid search on 2022-2023 "
                          "(log_loss=1.0629, beats Poisson's naive reference). Full walk-forward TEST-set "
                          "backtest (2023-2025) did not finish in time for this run: weekly MLE refits are "
                          "far slower than the closed-form Poisson. Currently serves live predictions in "
                          "the API without a completed out-of-sample TEST score yet — flagged here rather "
                          "than presented as backtested.",
            },
        ],
    }


@app.get("/health")
def health():
    return {"status": "ok", "phase": 1}
