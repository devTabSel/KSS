from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from kss.db import engine, get_session
from kss.main import app
from kss.models.base import Base
import kss.models  # noqa: F401

TEST_SCHEMA = "kss_pytest"


@pytest.fixture
def session() -> Generator[Session, None, None]:
    with engine.connect() as connection:
        connection.execute(text(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE"))
        connection.execute(text(f"CREATE SCHEMA {TEST_SCHEMA}"))
        connection.commit()
        trans = connection.begin()
        connection.execute(text(f"SET LOCAL search_path TO {TEST_SCHEMA}"))
        Base.metadata.create_all(bind=connection)
        SessionFactory = sessionmaker(
            bind=connection,
            join_transaction_mode="create_savepoint",
        )
        db_session = SessionFactory()
        try:
            yield db_session
        finally:
            db_session.close()
            trans.rollback()


@pytest.fixture
def client(session: Session) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
