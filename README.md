# Pari Futé — Terminal d'analyse football (Phase 1: Premier League MVP)

Système quantitatif de prédiction football. Les probabilités affichées
proviennent uniquement du moteur statistique (Poisson / Dixon-Coles), jamais
d'un LLM. Voir `docs/PHASE1_STATUS.md` pour l'état détaillé et les limites
connues.

## Lancer en local

```bash
pip install -r requirements.txt

# 1. Ingérer les données réelles (déjà fait, commité dans data/raw/)
python3 jobs/ingest_football_data_csv.py

# 2. Backend API
uvicorn backend.api.main:app --reload --port 8000

# 3. Frontend
cd frontend && npm install && npm run dev
```

Ou via Docker :

```bash
docker compose up --build
```

## Tests

```bash
pytest tests/ -v
```

## Ce qui est réellement implémenté (Phase 1)

- Ingestion de 4 saisons réelles Premier League (football-data.co.uk)
- Modèle Poisson (baseline) et Dixon-Coles (avec décroissance temporelle
  choisie par validation, pas arbitraire)
- Elo rating dynamique
- Backtest walk-forward strict (aucune fuite de données future)
- API FastAPI : `/matches`, `/matches/{id}/prediction`, `/matches/{id}/elo`,
  `/model/performance` — retourne explicitement "Donnée indisponible" (HTTP
  501) pour cotes/blessures/compositions, jamais de valeur inventée
- Frontend Next.js minimal (Home + page match) branché sur l'API réelle

## Ce qui n'est PAS encore implémenté

Voir `docs/PHASE1_STATUS.md`. En résumé : cotes de marché, compositions,
blessures, calibration (isotonic/Platt), simulations Monte-Carlo, ensemble
de modèles, ML (XGBoost/LightGBM), explicabilité SHAP, La Liga, Ligue 1.
