from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app

TEST_DB_NAME = f"{settings.postgres_db}_test"


def _ensure_test_database() -> None:
    """Cria a BD de testes se ainda não existir (numa BD separada da de desenvolvimento)."""
    admin_url = settings.database_url.set(database="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": TEST_DB_NAME}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin_engine.dispose()


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    _ensure_test_database()
    test_url = settings.database_url.set(database=TEST_DB_NAME)
    # Guarda de segurança: nunca correr (e apagar tabelas) na BD de desenvolvimento.
    assert test_url.database.endswith("_test")
    test_engine = create_engine(test_url)
    Base.metadata.create_all(test_engine)
    yield test_engine
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    """Sessão isolada: tudo o que o teste (e a API) gravar é revertido no fim.

    Os commits feitos pela API tornam-se SAVEPOINTs dentro de uma transação
    externa que fazemos rollback no fim de cada teste.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
