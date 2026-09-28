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


class InvalidTransitionError(DomainError):
    """A transição de estado pedida não é permitida pelo workflow."""

    def __init__(self, current: str, target: str, allowed: list[str]) -> None:
        self.current = current
        self.target = target
        self.allowed = allowed
        options = ", ".join(allowed) if allowed else "none (terminal state)"
        super().__init__(f"Cannot move incident from '{current}' to '{target}'. Allowed: {options}")


class IncidentClosedError(DomainError):
    """Um incidente fechado é um registo final e já não pode ser alterado."""

    def __init__(self, incident_id: int) -> None:
        self.incident_id = incident_id
        super().__init__(f"Incident {incident_id} is closed and can no longer be modified")


class TooManyLoginAttemptsError(DomainError):
    """Demasiadas tentativas de login falhadas; é preciso esperar."""

    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        minutes = -(-retry_after_seconds // 60)  # arredonda para cima
        unit = "minute" if minutes == 1 else "minutes"
        super().__init__(f"Too many failed login attempts. Try again in {minutes} {unit}.")


class DuplicateUserError(DomainError):
    """Já existe um utilizador com este email."""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"A user with email {email} already exists")


class LastAdminError(DomainError):
    """Esta alteração deixaria a aplicação sem nenhum administrador ativo."""

    def __init__(self) -> None:
        super().__init__("Cannot remove or deactivate the last active administrator")
