"""Database engine, session factory and declarative base."""
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

# Predictable constraint names make the schema easier to read and to migrate later.
NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def build_engine(url: str):
    if url.startswith("sqlite"):  # used by the automated tests only
        from sqlalchemy.pool import StaticPool

        return create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        echo=settings.db_echo,
        # Fail with a clear error instead of hanging: 10 s to connect, 15 s to wait for a table lock.
        connect_args={"connect_timeout": 10, "options": "-c lock_timeout=15000"},
    )


engine = build_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


def get_db():
    """FastAPI dependency: one database session per HTTP request.

    Anything not committed by the endpoint is rolled back, so a failed request
    never leaves a half-finished workflow change behind (NFR-REL-002).
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
