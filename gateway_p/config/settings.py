from typing import Dict, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = ""
    REDIS_URL: str = ""

    # Security
    SECRET_KEY: str = ""
    OPENAPI_TOKEN: str = ""
    DOCS_ENABLED: bool = False

    ALGORITHM: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    EMAIL_VERIFICATION_EXPIRE_MINUTES: int = 60 * 24
    # EMAIL_VERIFICATION_BASE_URL: str = ""
    EMAIL_VERIFICATION_BASE_URL: str = ""

    # Email Configuration
    EMAIL_ENABLED: bool = True  # Cambiar a True para habilitar envío real
    EMAIL_PROVIDER: str = "brevo"  # "brevo", "sendgrid" o "smtp"
    
    # Brevo API (antes Sendinblue - MÁS SIMPLE, 300 emails/día gratis)
    BREVO_API_KEY: str = ""
    BREVO_FROM_EMAIL: str = ""
    BREVO_FROM_NAME: str = ""
    
    # SendGrid API (Producción - requiere verificación)
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = ""
    SENDGRID_FROM_NAME: str = ""
    
    # SMTP Configuration (Legacy - solo para desarrollo)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""  # App Password si usas Gmail
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = ""

    # Infrastructure
    API_PORT: int = 8000

    # Banco Comercio credentials
    bdc_base_url_test: str = ""
    bdc_base_url: str = ""
    bdc_base_url_prod: str = ""
    bdc_client_id: str = ""
    bdc_client_secret: str = ""
    bdc_secret_key: str = ""
    
    # Banco Comercio SSL Certificates (None = sin certificados)
    bdc_client_cert_path: str = ""
    bdc_client_key_path: str = ""
    
    api_cert_ca: str = ""
    api_cert_client_key: str = ""
    api_cert_client_csr: str = ""
    api_cert_client_crt: str = ""

    transfer_connector_mode: str = ""
    persistence_backend: str = ""
    
    # PagoFlex Settings
    BDC_ALIAS_SUFFIX: str = ""  # Sufijo para alias generados
    bdc_test_cbu: str = ""  # CBU de testing para validación con BDC
    
     # KYC - Didit
    DIDIT_API_KEY: str = ""
    DIDIT_BASE_URL: str = ""
    DIDIT_WORKFLOW_ID: str = ""
    DIDIT_CALLBACK_URL: str = ""
    DIDIT_WEBHOOK_SECRET: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()
