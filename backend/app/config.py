from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    """Configuração da aplicação, lida de variáveis de ambiente.

    Em Docker as variáveis vêm do .env (via env_file no docker-compose).
    Campos sem valor por omissão são obrigatórios: se faltarem, a app
    falha ao arrancar em vez de correr mal configurada.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "db"
    postgres_port: int = 5432

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
