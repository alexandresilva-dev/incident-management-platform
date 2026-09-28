class DomainError(Exception):
    """Base dos erros de regras de negócio.

    Os serviços levantam estas exceções sem saberem nada de HTTP; a camada
    api/ (api/errors.py) traduz-as em respostas.
    """


class UnknownReferenceError(DomainError):
    """O pedido refere ids (ativos, vulnerabilidades...) que não existem."""

    def __init__(self, kind: str, missing_ids: list[int]) -> None:
        self.kind = kind
        self.missing_ids = missing_ids
        ids = ", ".join(str(i) for i in missing_ids)
        super().__init__(f"Unknown {kind} id(s): {ids}")
