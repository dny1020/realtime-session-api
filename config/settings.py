from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
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
    
    # Database pooling (already configured in database.py)
    db_pool_size: int = Field(default=20, description="Database connection pool size")
    db_max_overflow: int = Field(default=10, description="Database max overflow connections")
    db_pool_recycle: int = Field(default=3600, description="Recycle connections after N seconds")
    
    # Redis (for rate limiting, distributed locking, caching)
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )

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

    # JWT
    secret_key: str = Field(
        description="JWT secret key (REQUIRED - generate with: openssl rand -hex 32)"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration in minutes")
    refresh_token_expire_days: int = Field(default=7, description="Refresh token expiration in days")
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

    # Rate limiting (now using Redis)
    rate_limit_requests: int = Field(default=10, description="Rate limit requests per window")
    rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")
    
    # Brute force protection
    max_failed_login_attempts: int = Field(default=5, description="Max failed login attempts before lockout")
    login_lockout_duration: int = Field(default=900, description="Login lockout duration in seconds (15 min)")
    
    # Metrics
    metrics_enabled: bool = Field(default=True, description="Enable Prometheus metrics endpoint")

    # Asterisk connection pooling
    ari_max_keepalive: int = Field(default=20, description="Max keepalive connections to ARI")
    ari_max_connections: int = Field(default=50, description="Max total connections to ARI")
    
    # Circuit breaker configuration
    circuit_breaker_enabled: bool = Field(default=True, description="Enable circuit breaker for Asterisk")
    circuit_breaker_fail_threshold: int = Field(default=5, description="Failures before opening circuit")
    circuit_breaker_timeout: int = Field(default=60, description="Seconds before trying again")
    
    # Caching
    cache_enabled: bool = Field(default=True, description="Enable Redis caching")
    cache_ttl_call_status: int = Field(default=30, description="Cache TTL for call status (seconds)")
    
    # Data retention
    call_retention_days: int = Field(default=90, description="Days to retain call records")
    cleanup_interval_minutes: int = Field(default=60, description="Interval between cleanup runs")
    
    # Secrets management
    use_secrets_manager: bool = Field(default=False, description="Use external secrets manager")
    secrets_manager_type: str = Field(default="aws", description="Type: aws, vault, gcp")
    aws_secrets_region: Optional[str] = Field(default=None, description="AWS region for secrets")
    vault_url: Optional[str] = Field(default=None, description="Vault URL")
    vault_token: Optional[str] = Field(default=None, description="Vault token")
    
    # Observability
    otel_enabled: bool = Field(default=False, description="Enable OpenTelemetry tracing")
    otel_endpoint: Optional[str] = Field(default=None, description="OpenTelemetry collector endpoint")
    otel_service_name: str = Field(default="contact-center-api", description="Service name for tracing")

    @field_validator('secret_key')
    @classmethod
    def validate_secret_strength(cls, v, info):
        """Prevent weak secrets in production"""
        if info.data.get('debug', False):
            return v  # Allow anything in debug mode
        
        # Check length
        if len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters. "
                "Generate with: openssl rand -hex 32"
            )
        
        # Check for weak patterns
        weak = ['password', '123456', 'admin', 'test', 'secret', 
                'change', 'your-secret', 'CHANGE_ME']
        for pattern in weak:
            if pattern in v.lower():
                raise ValueError(
                    f"SECRET_KEY contains weak pattern. "
                    f"Generate strong key: openssl rand -hex 32"
                )
        
        # Check entropy (character diversity)
        if len(set(v)) < 16:
            raise ValueError(
                "SECRET_KEY too repetitive. "
                "Generate random key: openssl rand -hex 32"
            )
        
        return v
    
    @field_validator('allowed_origins')
    @classmethod
    def validate_cors(cls, v, info):
        """Prevent wildcard CORS in production"""
        if info.data.get('debug', False):
            return v
        
        if '*' in v:
            raise ValueError(
                "Wildcard CORS not allowed in production. "
                "Set specific domains: https://app.example.com"
            )
        
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Function to get the settings (useful for dependency injection)"""
    return settings
