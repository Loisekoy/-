import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")

from backend.database import get_db  # noqa: E402
from backend.main import create_app  # noqa: E402
from backend.models import Base  # noqa: E402
from backend.seed import seed_database  # noqa: E402


@pytest.fixture
def db_factory() -> Generator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        seed_database(db)
    yield factory
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(db_factory: sessionmaker[Session]) -> Generator[TestClient]:
    app = create_app()

    def override_get_db() -> Generator[Session]:
        with db_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
