"""
Configuration management for School Management Chatbot.
"""
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings with validation."""
    
    # Database Configuration
    database_host: str = Field(..., env="DATABASE_HOST")
    database_port: int = Field(5432, env="DATABASE_PORT")
    database_user: str = Field(..., env="DATABASE_USER")
    database_password: str = Field(..., env="DATABASE_PASSWORD")
    database_name: str = Field(..., env="DATABASE_NAME")
    database_pool_size: int = Field(10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(20, env="DATABASE_MAX_OVERFLOW")
    
    # JWT Configuration
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(60, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    # API Keys
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    google_api_key: Optional[str] = Field(None, env="GOOGLE_API_KEY")
    
    # LangSmith
    langchain_tracing_v2: bool = Field(True, env="LANGCHAIN_TRACING_V2")
    langchain_endpoint: str = Field("https://api.smith.langchain.com", env="LANGCHAIN_ENDPOINT")
    langchain_api_key: Optional[str] = Field(None, env="LANGCHAIN_API_KEY")
    langchain_project: str = Field("school-chatbot", env="LANGCHAIN_PROJECT")
    
    # Langfuse
    langfuse_public_key: Optional[str] = Field(None, env="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: Optional[str] = Field(None, env="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field("https://cloud.langfuse.com", env="LANGFUSE_HOST")
    
    # Redis
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    redis_cache_ttl: int = Field(3600, env="REDIS_CACHE_TTL")
    
    # Application
    app_name: str = Field("School Management Chatbot", env="APP_NAME")
    app_version: str = Field("1.0.0", env="APP_VERSION")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    
    # Security
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )
    api_rate_limit: int = Field(100, env="API_RATE_LIMIT")
    enable_content_filter: bool = Field(True, env="ENABLE_CONTENT_FILTER")
    
    # LLM Settings
    default_model: str = Field("claude-sonnet-4-20250514", env="DEFAULT_MODEL")
    llm_provider: str = Field("google", env="LLM_PROVIDER")
    temperature: float = Field(0.7, env="TEMPERATURE")
    max_tokens: int = Field(4096, env="MAX_TOKENS")
    max_iterations: int = Field(10, env="MAX_ITERATIONS")
    timeout_seconds: int = Field(120, env="TIMEOUT_SECONDS")
    
    # Multi-tenant
    default_schema: str = Field("public", env="DEFAULT_SCHEMA")
    enable_schema_isolation: bool = Field(True, env="ENABLE_SCHEMA_ISOLATION")
    
    @property
    def database_url(self) -> str:
        """Get database URL."""
        return (
            f"postgresql+asyncpg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )
    
    @property
    def sync_database_url(self) -> str:
        """Get synchronous database URL."""
        return (
            f"postgresql://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()
    
    @validator("llm_provider")
    def validate_llm_provider(cls, v):
        """Validate LLM provider."""
        valid_providers = ["anthropic", "openai", "google"]
        if v.lower() not in valid_providers:
            raise ValueError(f"LLM provider must be one of {valid_providers}")
        return v.lower()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings