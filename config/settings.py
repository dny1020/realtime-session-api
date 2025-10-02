from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file"""

    # Application
    app_name: str = Field(default="Contact Center API", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    docs_enabled: bool = Field(default=True, description="Enable OpenAPI docs (/docs, /redoc)")
    # Comma-separated in env: e.g., "https://api.example.com,https://app.example.com"
    allowed_origins: List[str] = Field(default_factory=lambda: ["*"], description="CORS allowed origins")

    # PostgreSQL database
    database_url: str = Field(
        default="postgresql://contact_center:contact123@localhost:5432/contact_center_db",
        description="PostgreSQL connection URL"
    )
    disable_db: bool = Field(default=False, description="Disable database usage (minimal mode)")

    # Asterisk host (for reference/logs)
    asterisk_host: str = Field(default="localhost", description="Asterisk host")
    # ARI (REST/WebSocket) configuration
    ari_http_url: str = Field(default="http://localhost:8088/ari", description="Base URL for ARI")
    ari_username: str = Field(default="ariuser", description="ARI username")
    ari_password: str = Field(default="aripass", description="ARI password")
    ari_app: str = Field(default="contactcenter", description="ARI application name (Stasis)")

    # Default call configuration
    default_context: str = Field(default="outbound-ivr", description="Default context")
    default_extension: str = Field(default="s", description="Default extension")
    default_priority: int = Field(default=1, description="Default priority")
    default_timeout: int = Field(default=30000, description="Default timeout in ms")
    default_caller_id: str = Field(default="Outbound Call", description="Default caller ID")

    # Campaign configuration removed (single-call API)

    # JWT
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="JWT secret key"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration in minutes")
    jwt_issuer: Optional[str] = Field(default=None, description="JWT issuer (iss)")
    jwt_audience: Optional[str] = Field(default=None, description="JWT audience (aud)")

    
    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    log_file: Optional[str] = Field(default=None, description="Log file")
    log_format: Optional[str] = Field(default=None, description="Optional log format for uvicorn/logging")

    # Uvicorn workers (if run under uvicorn directly; typically handled by process manager)
    workers: int = Field(default=1, description="Number of Uvicorn workers")

    # Files
    upload_dir: str = Field(default="./uploads", description="Upload directory")
    audio_dir: str = Field(default="./audio", description="Audio files directory")

    # Prometheus
    metrics_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=8001, description="Port for metrics")

    # Rate limiting
    rate_limit_requests: int = Field(default=10, description="Rate limit requests per window")
    rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")

    # Asterisk connection pooling
    ari_max_keepalive: int = Field(default=20, description="Max keepalive connections to ARI")
    ari_max_connections: int = Field(default=50, description="Max total connections to ARI")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Function to get the settings (useful for dependency injection)"""
    return settings