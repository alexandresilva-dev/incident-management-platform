"""Importar todos os modelos aqui garante que ficam registados em Base.metadata
(o Alembic precisa disso para os ver)."""

from app.models.asset import Asset

__all__ = ["Asset"]
