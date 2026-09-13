# Pari Futé — Statut Phase 1 (Premier League MVP)

## Ce qui fonctionne aujourd'hui

- **Données réelles** : 4 saisons Premier League (2021-2022 → 2024-2025, 1520 matchs)
  téléchargées depuis football-data.co.uk (`data/raw/E0_*.csv`), aucune donnée
  inventée. Ingestion vers `data/processed/matches.parquet`
  (`jobs/ingest_football_data_csv.py`).
- **Schéma PostgreSQL complet** (`backend/db/schema.sql`), multi-league dès le
  départ, avec contrainte SQL forçant `generated_at <= kickoff_utc` sur les
  prédictions.
- **Modèle baseline Poisson** (`ml/models/poisson_baseline.py`) : forces
  offensive/défensive domicile/extérieur, xG, 1X2, Over/Under 2.5, BTTS, top 5
  scores exacts.
- **Backtest walk-forward réel** (`ml/evaluation/backtest_poisson.py`) :
  refit hebdomadaire strictement sur l'historique antérieur, saison 2021-2022
  utilisée uniquement comme warm-up (non évaluée). Résultat sur 1140 matchs
  tenus à l'écart :
  - Log Loss : **1.1215**
  - Brier Score : **0.5983**
  - Accuracy : **0.5377**
- **Tests anti-data-leakage** (`tests/test_no_leakage.py`, 5/5 passent) :
  pas de doublons, probabilités ~1, preuve que `fit()` ignore les données
  futures, split chronologique strict, contrat timestamp < kickoff.

## Résultat honnête à ne pas cacher

Le Poisson simple **bat la précision naïve** (53,8 % vs ~46 % pour un modèle
qui prédirait toujours le taux de base historique) mais son **Log Loss est
pire** que cette même référence naïve (1.12 vs ~1.03). Cela indique une
**mauvaise calibration** (probabilités trop tranchées ou mal centrées), pas
un problème de fuite de données. C'est attendu pour une baseline non
calibrée : c'est précisément pour cela que Dixon-Coles puis la calibration
(isotonic/Platt) sont les étapes suivantes, et pas un ensemble ML prématuré.

## Ce qui N'EST PAS encore implémenté

- Dixon-Coles (correction low-score + pondération temporelle) — étape suivante.
- Elo rating dynamique / force des adversaires.
- Cotes de marché (`odds`) : aucune source légale branchée → toute demande
  de cote doit retourner **"Donnée indisponible"**, jamais une valeur inventée.
- Compositions, blessures, suspensions : tables créées mais vides.
- Calibration (isotonic/Platt), Monte-Carlo, ensemble, ML (XGBoost/LightGBM).
- API FastAPI et frontend Next.js : pas encore commencés.
- Base PostgreSQL réelle : schéma prêt, mais l'ingestion actuelle reste au
  format parquet local le temps de valider la baseline (éviter de complexifier
  avant que le modèle ait un intérêt mesurable).
- AI Confidence Score, explications SHAP, analyse tactique.
- La Liga, Ligue 1 (volontairement hors scope tant que Premier League n'est
  pas calibrée et backtestée de façon satisfaisante).

## Prochaine étape proposée

Implémenter Dixon-Coles (correction des scores faibles + décroissance
temporelle des poids, validée empiriquement et non fixée arbitrairement),
puis comparer son Log Loss/Brier/calibration au Poisson ci-dessus avant de
passer à quoi que ce soit d'autre.
