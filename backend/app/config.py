from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    """Configuração da aplicação, lida de variáveis de ambiente.

    Em Docker as variáveis vêm do .env (via env_file no docker-compose).
    Campos sem valor por omissão são obrigatórios: se faltarem, a app
    falha ao arrancar em vez de correr mal configurada.
    """

    # hide_input_in_errors: se um valor for inválido, o erro não o imprime
    # (evita que uma SECRET_KEY acabe nos logs).
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "db"
    postgres_port: int = 5432

    # Assina os tokens JWT. Obrigatória, sem valor por omissão (ver o validador).
    secret_key: str
    access_token_expire_minutes: int = 60

    # Só usadas por `python -m scripts.seed` para criar um utilizador de demonstração.
    seed_user_email: str | None = None
    seed_user_password: str | None = None

    # Origens (separadas por vírgula) autorizadas a chamar a API a partir de um browser.
    cors_origins: str = "http://localhost:5173"

    @field_validator("secret_key")
    @classmethod
    def _secret_key_must_be_strong(cls, value: str) -> str:
        if value.startswith("replace-with") or len(value) < 32:
            raise ValueError(
                "SECRET_KEY must be a random string of at least 32 characters "
                "(generate one with: openssl rand -hex 32)"
            )
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def database_url(self) -> URL:
        # URL.create escapa caracteres especiais da password, ao contrário
        # de uma f-string, que partia com uma password que contivesse "@" ou "/".
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


settings = Settings()
