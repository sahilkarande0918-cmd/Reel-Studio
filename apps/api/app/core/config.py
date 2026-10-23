from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).parents[2] / ".env", extra="ignore")

    supabase_url: str = ""
    supabase_secret_key: str = ""
    token_encryption_key: str = ""
    instagram_client_id: str = ""
    instagram_client_secret: SecretStr = SecretStr("")
    instagram_redirect_uri: str = ""
    instagram_api_version: str = "v24.0"
    google_client_id: str = ""
    google_client_secret: SecretStr = SecretStr("")
    google_redirect_uri: str = ""
    allowed_origins: str = "http://localhost:3000"
    data_dir: Path = Path("./data")
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5vl:7b"
    # Optional OpenAI-compatible endpoint for stronger creative planning (Mode B director). Empty = local Ollama only.
    director_api_url: str = ""
    director_api_key: SecretStr = SecretStr("")
    director_model: str = ""
    public_api_url: str = ""
    whisper_model: str = "large-v3-turbo"  # or a path to a converted CTranslate2 model directory
    whisper_device: str = "cuda"
    whisper_compute_type: str = "float16"
    whisper_language: str = ""  # empty = auto-detect per file

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_secret_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
