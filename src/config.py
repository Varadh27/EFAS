from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Enterprise Financial Audit & Variance System"
    environment: str = "development"
    database_url: str = (
        "postgresql://audit_admin:audit_secret_pw@localhost:5432/"
        "enterprise_audit_db"
    )
    openai_api_key: str = "dummy_key"
    materiality_threshold_dollars: float = 5000.00
    materiality_threshold_percent: float = 2.0


settings = Settings()
