from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str
    postgres_user: str = "vigia"
    postgres_db: str = "vigia_db"
    postgres_password: str = ""  # opcional quando DATABASE_URL é injetado direto (Render/Railway)

    # Cache e fila
    redis_url: str = "redis://localhost:6379"

    # Auth
    jwt_secret: str
    jwt_expire_hours: int = 24
    jwt_refresh_days: int = 30

    # IA
    anthropic_api_key: str

    # Satélite
    gee_service_account: str = ""
    gee_key_file: str = "./gee_key.json"

    # Notificações — Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = "whatsapp:+14155238886"
    twilio_sms_from: str = ""

    # Notificações — Z-API (alternativa BR)
    zapi_instance_id: str = ""
    zapi_token: str = ""

    # Destinatários — lista separada por vírgula, ex: "+5511999999999,+5511888888888"
    notificacao_destinos_whatsapp: str = ""
    notificacao_destinos_sms: str = ""

    # Monitoramento
    sentry_dsn: str = ""

    # App
    app_env: str = "development"
    app_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    relatorio_hora: str = "05:30"
    relatorio_timezone: str = "America/Sao_Paulo"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
