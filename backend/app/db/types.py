from enum import Enum as PyEnum

from sqlalchemy import Enum


def str_enum(enum_cls: type[PyEnum]) -> Enum:
    """Coluna de enum guardada como VARCHAR (e não como ENUM nativo do Postgres).

    Acrescentar um valor a um ENUM nativo exige ALTER TYPE, que é incómodo em
    migrações. Com VARCHAR basta atualizar o enum Python; a validação dos
    valores é feita pelo SQLAlchemy e pelo Pydantic.
    """
    return Enum(
        enum_cls,
        native_enum=False,
        length=32,
        validate_strings=True,
        # Guarda o valor ("high"), não o nome do membro do enum.
        values_callable=lambda cls: [member.value for member in cls],
    )
