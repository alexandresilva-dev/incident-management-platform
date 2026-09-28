from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.services.errors import (
    IncidentClosedError,
    InvalidTransitionError,
    TooManyLoginAttemptsError,
    UnknownReferenceError,
)


def register_exception_handlers(app: FastAPI) -> None:
    """Traduz erros de domínio (services/) em respostas HTTP."""

    @app.exception_handler(UnknownReferenceError)
    async def unknown_reference_handler(request: Request, exc: UnknownReferenceError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": str(exc)},
        )

    @app.exception_handler(InvalidTransitionError)
    async def invalid_transition_handler(request: Request, exc: InvalidTransitionError):
        # 409 Conflict: o pedido é válido, mas conflitua com o estado atual do recurso.
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc), "allowed_transitions": exc.allowed},
        )

    @app.exception_handler(IncidentClosedError)
    async def incident_closed_handler(request: Request, exc: IncidentClosedError):
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})

    @app.exception_handler(TooManyLoginAttemptsError)
    async def too_many_login_attempts_handler(request: Request, exc: TooManyLoginAttemptsError):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": str(exc)},
            headers={"Retry-After": str(exc.retry_after_seconds)},
        )
