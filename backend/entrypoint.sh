#!/bin/sh
# Applies the schema and loads real historical data into whatever Postgres
# DATABASE_URL points to, then starts the API. Idempotent: schema uses
# CREATE TABLE (fails silently if already applied, ignored below) and the
# loader uses ON CONFLICT DO NOTHING.
set -e

python3 - <<'PYEOF'
import os
import psycopg2

url = os.environ.get("DATABASE_URL", "postgresql://pari_fute:pari_fute@localhost:5432/pari_fute")
if url.startswith("postgresql+psycopg2://"):
    url = url.replace("postgresql+psycopg2://", "postgresql://", 1)

conn = psycopg2.connect(url)
conn.autocommit = False
try:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'matches')"
        )
        exists = cur.fetchone()[0]

    if not exists:
        print("Schema not found — applying backend/db/schema.sql ...")
        with open("backend/db/schema.sql") as f:
            schema_sql = f.read()
        with conn.cursor() as cur:
            cur.execute(schema_sql)  # psycopg2 supports multi-statement scripts
        conn.commit()
    else:
        print("Schema already present — skipping.")
finally:
    conn.close()
PYEOF

python3 -m jobs.load_matches_to_postgres

exec uvicorn backend.api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
