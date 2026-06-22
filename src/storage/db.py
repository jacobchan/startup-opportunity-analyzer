from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
_engine = None
_SessionLocal = None
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_engine(db_path: str | None = None):
    global _engine
    if _engine is None:
        if db_path is None:
            # Keep history stable even when uvicorn/CLI is launched from a
            # different working directory.
            db_path = str(_PROJECT_ROOT / "data" / "analyzer.db")
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
    eng = engine or get_engine()
    Base.metadata.create_all(eng)
    _run_lightweight_migrations(eng)


def _run_lightweight_migrations(engine) -> None:
    """Add columns that were introduced after the initial schema."""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    if "runs" not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns("runs")}
    with engine.begin() as conn:
        if "deliberation_state" not in existing:
            conn.execute(text("ALTER TABLE runs ADD COLUMN deliberation_state JSON"))
