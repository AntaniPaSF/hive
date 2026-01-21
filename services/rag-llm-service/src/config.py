"""Configuration management for RAG LLM Service."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings can be configured via environment variables or .env file.
    """

    # Ollama Configuration
    ollama_host: str = Field(
        default="http://localhost:11434", description="Ollama API endpoint"
    )
    ollama_model: str = Field(
        default="mistral:7b", description="Ollama model to use for generation"
    )
    ollama_timeout: int = Field(
        default=30, description="Ollama generation timeout in seconds"
    )

    # Vector Store Configuration
    vector_store_url: str = Field(
        default="http://localhost:8001", description="ChromaDB vector store URL"
    )
    vector_store_collection: str = Field(
        default="hr_documents", description="ChromaDB collection name"
    )
    vector_store_timeout: int = Field(
        default=10, description="Vector store query timeout in seconds"
    )
    max_retrieved_chunks: int = Field(
        default=5, description="Maximum number of chunks to retrieve per query"
    )

    # Embedding Configuration
    embedding_api_url: str = Field(
        default="http://localhost:8002/embed",
        description="HR Data Pipeline embedding API endpoint",
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2", description="Embedding model name (for validation)"
    )
    embedding_dimension: int = Field(
        default=384, description="Expected embedding dimension"
    )
    embedding_api_timeout: int = Field(
        default=5, description="Embedding API timeout in seconds"
    )

    # RAG Service Configuration
    min_confidence_threshold: float = Field(
        default=0.5, description="Minimum confidence threshold for returning answers"
    )
    rag_service_port: int = Field(default=8000, description="RAG service HTTP port")

    # Logging Configuration
    log_level: str = Field(
        default="INFO", description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    log_format: str = Field(default="json", description="Log format (json or text)")
    log_file: Optional[str] = Field(
        default=None, description="Log file path (None for stdout only)"
    )

    # API Configuration
    enable_cors: bool = Field(
        default=True, description="Enable CORS for FastAPI wrapper integration"
    )
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080",
        description="Comma-separated list of allowed CORS origins",
    )

    # Retry Configuration
    max_retries: int = Field(
        default=3, description="Maximum retries for failed API calls"
    )
    retry_backoff: int = Field(
        default=2, description="Retry backoff multiplier (exponential backoff)"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v_upper

    @field_validator("min_confidence_threshold")
    @classmethod
    def validate_confidence_threshold(cls, v: float) -> float:
        """Validate confidence threshold is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(
                f"Confidence threshold must be between 0.0 and 1.0, got {v}"
            )
        return v

    @field_validator("max_retrieved_chunks")
    @classmethod
    def validate_max_chunks(cls, v: int) -> int:
        """Validate max retrieved chunks is reasonable."""
        if v < 1:
            raise ValueError(f"max_retrieved_chunks must be at least 1, got {v}")
        if v > 10:
            raise ValueError(f"max_retrieved_chunks cannot exceed 10, got {v}")
        return v

    @field_validator("embedding_dimension")
    @classmethod
    def validate_embedding_dimension(cls, v: int) -> int:
        """Validate embedding dimension is 384 (all-MiniLM-L6-v2)."""
        if v != 384:
            raise ValueError(
                f"Embedding dimension must be 384 for all-MiniLM-L6-v2, got {v}"
            )
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        """Pydantic settings configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create global settings instance.

    Returns:
        Settings instance with loaded configuration
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment.

    Useful for testing or runtime configuration changes.

    Returns:
        New Settings instance
    """
    global _settings
    _settings = Settings()
    return _settings
