from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Nomes determinísticos para constraints. Sem isto o Postgres gera nomes
# automáticos, e o Alembic não consegue alterá-los/removê-los de forma fiável.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base de todos os modelos SQLAlchemy.

    O Alembic usa Base.metadata para saber que tabelas deviam existir.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
