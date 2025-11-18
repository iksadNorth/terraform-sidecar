from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """환경 설정."""

    terraform_root: Path = Path("/tfpjts")
    terraform_bin: str = "terraform"
    lock_dir: Path = Path("/tmp/tf_locks")
    lock_ttl_seconds: int = 3600
    git_clone_depth: int | None = None
    startup_init_enabled: bool = True

    model_config = SettingsConfigDict(env_prefix="SIDECAR_", extra="ignore")

    def ensure_directories(self) -> None:
        self.terraform_root.mkdir(parents=True, exist_ok=True)
        self.lock_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

