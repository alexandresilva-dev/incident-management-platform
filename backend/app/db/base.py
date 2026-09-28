from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base de todos os modelos SQLAlchemy.

    O Alembic usa Base.metadata para saber que tabelas deviam existir.
    """
