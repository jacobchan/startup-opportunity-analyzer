import pytest
from sqlalchemy import create_engine

from src.storage import db


@pytest.fixture(autouse=True)
def isolate_default_test_database(tmp_path, monkeypatch):
    """Never let tests create fake history in data/analyzer.db."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(db, "_engine", engine)
    monkeypatch.setattr(db, "_SessionLocal", None)
    db.init_db(engine)
    yield
    engine.dispose()
