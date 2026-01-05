from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Loaded from environment variables
    DATABASE_URL: str = (
        "postgresql+asyncpg://scheduler:scheduler@localhost:5432/scheduler"
    )

    # Allow local dev UI calls
    CORS_ORIGINS: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Scheduling safety caps (demo-safe defaults)
    MAX_TEAMS: int = 24
    MAX_VENUES: int = 12
    MAX_TIME_WINDOWS: int = 24
    MAX_MATCHUPS: int = 2000


settings = Settings()
