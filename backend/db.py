import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@lru_cache
def engine():
    url = os.environ.get("DATABASE_URL")
    if not url or not url.startswith("postgresql+psycopg://"):
        raise RuntimeError("Set DATABASE_URL to a PostgreSQL psycopg URL; SQLite is not supported")
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        connect_args={"options": "-c statement_timeout=5000 -c lock_timeout=3000"},
    )


def session():
    with Session(engine()) as db:
        yield db
