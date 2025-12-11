from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    POSTGRES_HOST: str = Field(..., env="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(5432, env="POSTGRES_PORT")
    POSTGRES_NAME: str = Field(..., env="POSTGRES_NAME")
    POSTGRES_USER: str = Field(..., env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(..., env="POSTGRES_PASSWORD")

    REDIS_HOST: str = Field("redis", env="REDIS_HOST")
    REDIS_PORT: int = Field(6379, env="REDIS_PORT")

    FERNET_KEY: str = Field(..., env="FERNET_KEY")
    JWT_SECRET: str = Field(..., env="JWT_SECRET")

    HUAWEI_API_URL: str = Field(
        "https://eu5.fusionsolar.huawei.com/thirdData", env="HUAWEI_API_URL"
    )

    LOG_DIR: str = Field("logs", env="LOG_DIR")

    NATS_URL: str = Field("nats://localhost:4222", env="NATS_URL")

    EMAIL_HOST: str = Field("smtp.example.com", env="EMAIL_HOST")
    EMAIL_PORT: int = Field(587, env="EMAIL_PORT")
    EMAIL_USER: str | None = Field(None, env="EMAIL_USER")
    EMAIL_PASSWORD: str | None = Field(None, env="EMAIL_PASSWORD")
    EMAIL_FROM: str = Field("no-reply@smartenergy.local", env="EMAIL_FROM")
    EMAIL_USE_TLS: bool = Field(True, env="EMAIL_USE_TLS")
    EMAIL_USE_SSL: bool = Field(False, env="EMAIL_USE_SSL")

    FRONTEND_URL: str = Field("http://localhost:5173", env="FRONTEND_URL")

    WDB_SOCKET_SERVER: str | None = Field(
        default=None, description="Host (Docker container) where wdb server runs"
    )
    WDB_NO_BROWSER_AUTO_OPEN: bool | None = Field(default=True)
    WDB_WEB_PORT: int | None = Field(default=1984)
    WDB_WEB_SERVER: str | None = Field(default="http://localhost")

    GET_PRODUCTION_INTERVAL_MINUTES: int = Field(3, env="GET_PRODUCTION_INTERVAL_MINUTES")

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:5432/{self.POSTGRES_NAME}"
        )

    model_config = {
        "extra": "ignore",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "from_attributes": True,
    }


settings = Settings()
