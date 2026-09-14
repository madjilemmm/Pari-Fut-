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

## Mise à jour — étapes calibration/simulation/ML/UI

- **Calibration** (`ml/evaluation/calibration.py`) : isotonic regression fit sur 70%
  chronologique du backtest Poisson, évaluée sur les 30% restants (jamais les mêmes
  matchs). Résultat réel : ECE=0.074, LogLoss calibré 0.6297 vs 0.6304 brut sur la
  même tranche — amélioration réelle mais modeste, à documenter honnêtement, pas
  à vendre comme une révolution.
- **Monte-Carlo** (`ml/simulations/monte_carlo.py`) : 50 000 tirages Poisson sur les
  xG Dixon-Coles, exposé via `GET /matches/{id}/simulations`.
- **Comparaison ML** (`ml/evaluation/compare_logistic_regression.py`) : Logistic
  Regression sur l'écart Elo walk-forward. Résultat réel sur 342 matchs tenus à
  l'écart : LogLoss=1.0064 vs référence Poisson 1.1215 — prometteur, mais comparé
  sur une fenêtre différente (30% chronologique vs backtest complet), donc **pas
  encore une preuve suffisante pour remplacer la baseline** ; nécessite un backtest
  walk-forward complet sur la même fenêtre avant adoption.
- **Page Model Performance** ajoutée au frontend (`/model-performance`), branchée
  sur `GET /model/performance` qui expose maintenant Poisson brut, Poisson calibré
  et le statut (encore incomplet) de Dixon-Coles.
- **Dixon-Coles TEST backtest COMPLET** (2023-2024 + 2024-2025, 760 matchs,
  walk-forward hebdomadaire, xi=0.005 choisi par validation sur 2022-2023) :
  terminé. Comparaison honnête sur exactement la même fenêtre que le Poisson :

  | Modèle | Log Loss | Brier | Accuracy |
  |---|---|---|---|
  | Poisson (edge_v0.1) | 0.9793 | 0.5817 | 55.79% |
  | Dixon-Coles (edge_v0.2) | **0.9575** | **0.5684** | 55.00% |

  Dixon-Coles gagne sur les deux métriques primaires du projet (Log Loss, Brier),
  l'accuracy est quasi identique (léger avantage Poisson, non significatif sur
  760 matchs). **Dixon-Coles devient donc le modèle par défaut** (déjà branché
  dans l'API). Ni l'un ni l'autre n'est encore calibré (isotonic) sur cette
  fenêtre précise — la calibration actuelle a été faite sur le Poisson et une
  fenêtre différente ; refaire la calibration sur Dixon-Coles est la suite
  logique.
- **PostgreSQL** : le schéma existe mais l'application tourne encore entièrement
  sur fichiers parquet locaux. Le branchement réel de Postgres (ingestion via
  SQLAlchemy, jobs d'écriture) reste à faire — prochaine étape technique prioritaire
  avant toute mise en production.

## Prochaine étape proposée

Implémenter Dixon-Coles (correction des scores faibles + décroissance
temporelle des poids, validée empiriquement et non fixée arbitrairement),
puis comparer son Log Loss/Brier/calibration au Poisson ci-dessus avant de
passer à quoi que ce soit d'autre.
