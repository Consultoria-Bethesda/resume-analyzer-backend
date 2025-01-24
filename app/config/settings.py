from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "development"
    
    # Database settings
    PGUSER: str = "postgres"
    PGPASSWORD: str = "postgres"
    PGHOST: str = "db"
    PGPORT: str = "5432"
    PGDATABASE: str = "resume_analyzer"
    
    # Alias para manter compatibilidade
    DB_USER: str = PGUSER
    DB_PASSWORD: str = PGPASSWORD
    DB_HOST: str = PGHOST
    DB_PORT: str = PGPORT
    DB_NAME: str = PGDATABASE

    # URLs
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"

    # Authentication
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    SECRET_KEY: str = "8f45d7f2a1b3c6e9d8a4b7c2e5f8a9d6b3c7e1f4a2d5b8e3f6c9a2d5b8e3f6"

    # OpenAI
    OPENAI_API_KEY: str | None = None

    # Stripe
    STRIPE_SECRET_KEY: str | None = None
    STRIPE_PUBLIC_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    STRIPE_PRICE_ID: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )

settings = Settings()
