import os
from dataclasses import dataclass


@dataclass
class AppConfig:
    # No hardcoded defaults: require env var or explicit .env file consumption by container
    # 0 means unset; start script enforces requirement
    app_port: int = int(os.environ.get("APP_PORT", "0"))

    @classmethod
    def validate(cls) -> "AppConfig":
        cfg = cls()
        if cfg.app_port == 0:
            # We do not fail here to allow container internal port usage; scripts enforce host port presence.
            pass
        return cfg
