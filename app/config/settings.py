from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    FRONTEND_URL: str
    BASE_URL: str
    
    # Variáveis do Railway
    PGHOST: str
    PGPORT: str
    PGUSER: str
    PGPASSWORD: str
    PGDATABASE: str
    
    OPENAI_API_KEY: str
    STRIPE_SECRET_KEY: str
    STRIPE_PUBLIC_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    STRIPE_PRICE_ID: str
    SECRET_KEY: str
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    ENVIRONMENT: str = "development"  # Valor padrão é development

    class Config:
        env_file = ".env"

    @property
    def DB_HOST(self) -> str:
        return self.PGHOST

    @property
    def DB_PORT(self) -> str:
        return self.PGPORT

    @property
    def DB_USER(self) -> str:
        return self.PGUSER

    @property
    def DB_PASSWORD(self) -> str:
        return self.PGPASSWORD

    @property
    def DB_NAME(self) -> str:
        return self.PGDATABASE

settings = Settings()
