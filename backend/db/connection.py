import os

from sqlalchemy import create_engine

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg2://pari_fute:pari_fute@localhost:5432/pari_fute"
)

# Managed Postgres providers (Render, Railway, Heroku, Neon) hand out
# "postgresql://" or "postgres://" URLs; SQLAlchemy needs the psycopg2 driver
# named explicitly.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
