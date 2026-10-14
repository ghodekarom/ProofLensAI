"""Application configuration management using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """ProofLens AI application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_ENV: str = Field(default="development", description="Environment: development, test, production")
    APP_NAME: str = Field(default="ProofLens AI", description="Service display name")
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    API_V1_PREFIX: str = Field(default="/api/v1", description="API v1 prefix")
    HOST: str = Field(default="0.0.0.0", description="Host to bind server")
    PORT: int = Field(default=8000, description="Port to bind server")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://prooflens:prooflens_local_only@localhost:5432/prooflens",
        description="SQLAlchemy PostgreSQL connection URL",
    )
    DB_POOL_SIZE: int = Field(default=5, description="Connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Max overflow connections")

    # Local File Storage
    FILE_STORAGE_BACKEND: str = Field(default="local", description="Storage backend type")
    LOCAL_STORAGE_PATH: str = Field(default="./var/uploads", description="Directory for uploaded PDFs")
    MAX_UPLOAD_BYTES: int = Field(default=20 * 1024 * 1024, description="Max upload file size in bytes (20MB)")
    MAX_BATCH_FILES: int = Field(default=10, description="Max files allowed in batch upload")
    MAX_PDF_PAGES: int = Field(default=500, description="Max page count per PDF")

    # Chunking & Retrieval
    CHUNK_SIZE_TOKENS: int = Field(default=800, description="Target token count per chunk")
    CHUNK_OVERLAP_TOKENS: int = Field(default=120, description="Token overlap between adjacent chunks")
    RETRIEVAL_TOP_K_DEFAULT: int = Field(default=5, description="Default number of passages to retrieve")
    RETRIEVAL_TOP_K_MAX: int = Field(default=20, description="Hard cap on retrieved passages")
    RETRIEVAL_DISTANCE_THRESHOLD: float | None = Field(
        default=None, description="Optional cosine distance threshold"
    )

    # Google Gemini AI Provider
    LLM_PROVIDER: str = Field(default="google_gemini", description="LLM provider name")
    LLM_MODEL: str = Field(default="gemini-3.5-flash-lite", description="Gemini LLM model name")
    LLM_TIMEOUT_SECONDS: int = Field(default=30, description="LLM request timeout")
    LLM_MAX_RETRIES: int = Field(default=2, description="Max retries for transient LLM errors")
    LLM_MAX_OUTPUT_TOKENS: int = Field(default=2048, description="Max generation output tokens")

    EMBEDDING_PROVIDER: str = Field(default="google_gemini", description="Embedding provider name")
    EMBEDDING_MODEL: str = Field(default="gemini-embedding-2", description="Embedding model name")
    EMBEDDING_DIMENSION: int = Field(default=768, description="Vector dimensions for pgvector column")
    EMBEDDING_BATCH_SIZE: int = Field(default=32, description="Batch size for embedding calls")

    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API key")

    @property
    def GOOGLE_API_KEY(self) -> str:  # noqa: N802 – mirror SDK naming
        """Alias for GEMINI_API_KEY used by the Gemini SDK."""
        return self.GEMINI_API_KEY

    # Security & CORS
    CORS_ORIGINS: list[str] | str = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins",
    )
    LOG_LEVEL: str = Field(default="INFO", description="Log verbosity")
    LOG_FORMAT: str = Field(default="json", description="Log format: json or console")

    @field_validator("RETRIEVAL_DISTANCE_THRESHOLD", mode="before")
    @classmethod
    def parse_empty_float(cls, v: Any) -> float | None:
        if v == "" or v is None:
            return None
        return float(v)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def TESTING(self) -> bool:  # noqa: N802
        """True when running inside test or CI environments."""
        return self.APP_ENV.lower() in {"test", "testing", "ci"}

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def is_test(self) -> bool:
        return self.APP_ENV.lower() == "test"

    def get_storage_path(self) -> Path:
        """Returns the absolute path to the local storage directory and ensures it exists."""
        path = Path(self.LOCAL_STORAGE_PATH).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    """Returns cached application settings instance."""
    return Settings()
