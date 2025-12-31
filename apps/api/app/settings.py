from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Loaded from environment variables
    DATABASE_URL: str = "postgresql+asyncpg://scheduler:scheduler@localhost:5432/scheduler"

    # Allow local dev UI calls
    CORS_ORIGINS: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
