import os
from dataclasses import dataclass


@dataclass
class AppConfig:
    # No hardcoded defaults: require env var or explicit .env file consumption by container
    # 0 means unset; start script enforces requirement
    app_port: int = int(os.environ.get("APP_PORT", "0"))
    
    # Data Pipeline Configuration (Text-based, no embeddings)
    vector_db_type: str = os.environ.get("VECTOR_DB_TYPE", "chromadb")
    vector_db_path: str = os.environ.get("VECTOR_DB_PATH", "/app/vectordb_storage")
    chunk_size: int = int(os.environ.get("CHUNK_SIZE", "512"))
    chunk_overlap: int = int(os.environ.get("CHUNK_OVERLAP", "50"))
    min_chunk_size: int = int(os.environ.get("MIN_CHUNK_SIZE", "100"))

    @classmethod
    def validate(cls) -> "AppConfig":
        cfg = cls()
        if cfg.app_port == 0:
            # We do not fail here to allow container internal port usage; scripts enforce host port presence.
            pass
        return cfg
