import os

from sqlalchemy import create_engine

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg2://pari_fute:pari_fute@localhost:5432/pari_fute"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
