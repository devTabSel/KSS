from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session, sessionmaker

from kss.db import engine
from kss.models.base import Base
import kss.models  # noqa: F401


@pytest.fixture
def session() -> Generator[Session, None, None]:
    with engine.connect() as connection:
        trans = connection.begin()
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
