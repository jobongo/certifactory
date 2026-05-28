from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./pki.db"
    PKI_MASTER_KEY: str = "CHANGE-ME-IN-PRODUCTION-32-BYTES"
    JWT_SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DEFAULT_CRL_REGEN_HOURS: int = 24
    EXPIRY_WARNING_DAYS: int = 30
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:5175"]
    SSL_CERT_DIR: str = "/etc/nginx/certs"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
