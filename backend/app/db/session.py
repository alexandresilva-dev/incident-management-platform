from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# pool_pre_ping testa a ligação antes de a usar, para recuperar sozinho
# se a BD reiniciar entretanto (em vez de falhar o primeiro pedido).
engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine)


def get_db() -> Iterator[Session]:
    """Dependência do FastAPI: uma sessão por pedido, fechada no fim."""
    with SessionLocal() as session:
        yield session
