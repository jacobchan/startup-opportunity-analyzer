from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
_engine = None
_SessionLocal = None


def get_engine(db_path: str | None = None):
    global _engine
    if _engine is None:
        if db_path is None:
            db_path = str(Path("data") / "analyzer.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
    return _engine


def get_session():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()


def init_db(engine=None):
    from src.storage.models import Run, Evidence, Challenge  # noqa
    Base.metadata.create_all(engine or get_engine())
