# Déployer Pari Futé (frontend sur Vercel + backend sur Render)

Vercel héberge très bien le **frontend Next.js**. Il n'est en revanche pas
adapté au **backend** de ce projet (FastAPI + PostgreSQL + calculs ML type
Dixon-Coles, qui prennent 1-2 secondes par requête et ne rentrent pas dans le
modèle serverless "cold start" de Vercel). Le screenshot d'échec de build que
vous avez eu ("No FastAPI entrypoint found") venait de Vercel qui essayait de
déployer tout le repo, y compris le backend.

La solution : **deux déploiements séparés**.

## 1. Backend + PostgreSQL sur Render (gratuit)

Un fichier `render.yaml` est déjà présent à la racine du repo — Render le
détecte automatiquement.

1. Allez sur https://render.com, connectez votre compte GitHub.
2. "New +" → "Blueprint" → sélectionnez le repo `madjilemmm/Pari-Fut-`,
   branche `claude/intelligent-hopper-o759ri` (ou `main` une fois mergé).
3. Render lit `render.yaml` et crée automatiquement :
   - une base PostgreSQL managée (`pari-fute-db`)
   - un service web Docker (`pari-fute-backend`) construit depuis
     `backend/Dockerfile`
4. Au premier démarrage, `backend/entrypoint.sh` applique automatiquement le
   schéma SQL et charge les 1520 vrais matchs Premier League déjà présents
   dans `data/raw/` — rien à faire manuellement.
5. Une fois déployé, notez l'URL du backend, par exemple :
   `https://pari-fute-backend.onrender.com`
6. Vérifiez que ça fonctionne : `https://pari-fute-backend.onrender.com/health`
   doit répondre `{"status":"ok","phase":1}`.

(Alternative équivalente à Render : Railway ou Fly.io — le principe est le
même, ce sont des plateformes qui font tourner un vrai conteneur Docker avec
PostgreSQL, contrairement à Vercel.)

## 2. Frontend sur Vercel

1. Sur https://vercel.com, "Add New..." → "Project" → importez le même repo.
2. **Important** : dans les réglages du projet Vercel, "Root Directory" →
   `frontend` (le repo est un monorepo ; sans ce réglage, Vercel essaie de
   builder le backend Python, d'où l'échec précédent).
3. Framework Preset : Next.js (détecté automatiquement une fois le Root
   Directory correct).
4. Ajoutez la variable d'environnement :
   - `NEXT_PUBLIC_API_URL` = l'URL Render du backend (ex :
     `https://pari-fute-backend.onrender.com`)
5. Déployez.

## Vérification

Une fois les deux déployés :
- `https://<votre-projet>.vercel.app/` doit afficher la liste des matchs
  Premier League réels
- Cliquer sur un match doit afficher les probabilités, xG, top 5 scores
- `https://<votre-projet>.vercel.app/model-performance` doit afficher la
  comparaison Poisson vs Dixon-Coles

Si la page affiche "Donnée indisponible — impossible de contacter l'API
backend", vérifiez `NEXT_PUBLIC_API_URL` dans les réglages Vercel et que le
backend Render répond bien sur `/health`.

## Limite connue

Le plan gratuit de Render met le service en veille après inactivité : la
première requête après une pause peut prendre 30-60s (cold start). Sur un
plan payant, ce n'est plus un problème. Ce n'est pas spécifique à ce
projet — n'importe quel backend Python sur un plan gratuit a ce comportement.
