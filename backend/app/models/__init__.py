"""Importar todos os modelos aqui garante que ficam registados em Base.metadata
(o Alembic precisa disso para os ver)."""

from app.models.asset import Asset
from app.models.vulnerability import Vulnerability

__all__ = ["Asset", "Vulnerability"]
