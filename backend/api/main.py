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


@app.get("/matches/{match_id}/why")
def get_why(match_id: str):
    try:
        return prediction_service.why_match(match_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Match introuvable")
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=501, detail=f"Donnée indisponible: {e}")


@app.get("/matches/{match_id}/form")
def get_form(match_id: str):
    try:
        return prediction_service.form_guide(match_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Match introuvable")


@app.get("/matches/{match_id}/power-rating")
def get_power_rating(match_id: str):
    try:
        return prediction_service.power_rating(match_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Match introuvable")
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=501, detail=f"Donnée indisponible: {e}")


@app.get("/leagues")
def get_leagues():
    return [
        {"code": "PL", "name": "Premier League", "flag": "🇬🇧", "status": "active"},
        {"code": "LL", "name": "La Liga", "flag": "🇪🇸", "status": "coming_soon"},
        {"code": "L1", "name": "Ligue 1", "flag": "🇫🇷", "status": "coming_soon"},
    ]


@app.get("/matches/{match_id}/odds")
def get_odds(match_id: str):
    raise HTTPException(status_code=501, detail="Donnée indisponible: aucun fournisseur de cotes configuré en Phase 1")


@app.get("/matches/{match_id}/injuries")
def get_injuries(match_id: str):
    raise HTTPException(status_code=501, detail="Donnée indisponible: aucune source de blessures configurée en Phase 1")


@app.get("/model/performance")
def get_model_performance():
    return {
        "note": "Nous publions les performances du modèle, y compris lorsqu'il se trompe. "
                "Toutes les métriques ci-dessous proviennent de backtests walk-forward réels "
                "(aucun match utilisé pour l'entraînement n'a servi à l'évaluation).",
        "current_model": {
            "display_name": "Dixon-Coles",
            "version": "edge_v0.2_dixon_coles",
            "n_predictions": 760,
            "accuracy": 0.5500,
            "log_loss": 0.9575,
            "brier_score": 0.5684,
            "evaluation_period": "Saisons 2023-2024 et 2024-2025 (760 matchs, jamais vus à l'entraînement)",
        },
        "models": [
            {
                "model_version": "edge_v0.1_poisson",
                "display_name": "Poisson",
                "evaluation_period": "test_2023_2024_and_2024_2025 (weekly walk-forward refit)",
                "n_predictions": 760,
                "log_loss": 0.9793,
                "brier_score": 0.5817,
                "accuracy": 0.5579,
                "status": "baseline",
            },
            {
                "model_version": "edge_v0.1_poisson_isotonic_calibrated",
                "display_name": "Poisson (calibré)",
                "evaluation_period": "held-out 30% chronological slice of the wider 2022-2025 backtest",
                "n_predictions": 342,
                "log_loss": 0.6297,
                "brier_score": 0.2202,
                "expected_calibration_error": 0.0740,
                "status": "calibration improves Brier/LogLoss vs raw on the same held-out slice (raw: LogLoss=0.6304, Brier=0.2205); see ml/evaluation/calibration.py",
            },
            {
                "model_version": "edge_v0.2_dixon_coles",
                "display_name": "Dixon-Coles",
                "evaluation_period": "test_2023_2024_and_2024_2025 (weekly walk-forward refit, xi=0.005 selected via 2022-2023 validation)",
                "n_predictions": 760,
                "log_loss": 0.9575,
                "brier_score": 0.5684,
                "accuracy": 0.5500,
                "is_current": True,
                "status": "CURRENT DEFAULT — beats Poisson on log loss and Brier (the project's primary "
                          "metrics) on the exact same test window; accuracy is essentially tied "
                          "(55.0% vs 55.8%). Not yet isotonic-calibrated. Served live by the API.",
            },
        ],
    }


@app.get("/model/calibration")
def get_model_calibration():
    """Real reliability-diagram points and ECE from ml/evaluation/calibration.py,
    computed on a held-out chronological slice never used to fit the isotonic
    calibrator. Hardcoded here because the backtest artifact this was computed
    from (data/processed/*.parquet) is a local, gitignored build output — the
    numbers themselves are real, just not recomputed on every request."""
    return {
        "model_version": "edge_v0.1_poisson",
        "note": "Quand Pari Futé annonce environ 60%, l'événement se produit-il réellement "
                "environ 60% du temps ? Ce graphique compare la probabilité annoncée (axe X) "
                "à la fréquence réellement observée (axe Y) sur des matchs jamais vus à l'entraînement.",
        "expected_calibration_error": 0.0611,
        "n_predictions": 1140,
        "reliability_curve": [
            {"predicted": 0.08, "observed": 0.18},
            {"predicted": 0.19, "observed": 0.14},
            {"predicted": 0.32, "observed": 0.32},
            {"predicted": 0.44, "observed": 0.46},
            {"predicted": 0.56, "observed": 0.49},
            {"predicted": 0.68, "observed": 0.53},
            {"predicted": 0.81, "observed": 0.75},
            {"predicted": 0.89, "observed": 1.00},
        ],
    }


@app.get("/health")
def health():
    return {"status": "ok", "phase": 1}
