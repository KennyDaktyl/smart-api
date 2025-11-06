from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_HOST: str = Field(..., env="DB_HOST")
    DB_PORT: int = Field(5432, env="DB_PORT")
    DB_NAME: str = Field(..., env="DB_NAME")
    DB_USER: str = Field(..., env="DB_USER")
    DB_PASSWORD: str = Field(..., env="DB_PASSWORD")

    FERNET_KEY: str = Field(..., env="FERNET_KEY")

    HUAWEI_API_URL: str = Field(
        "https://eu5.fusionsolar.huawei.com/thirdData", env="HUAWEI_API_URL"
    )

    LOG_DIR: str = Field("logs", env="LOG_DIR")

    NATS_URL: str = Field("nats://localhost:4222", env="NATS_URL")

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
