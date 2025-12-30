from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]

class Settings(BaseSettings):
    OPENAI_API_KEY: str | None = None

    DATABASE_URL: str = f"sqlite:///{(BASE_DIR / 'data' / 'chatbot.db').as_posix()}"
    VECTORSTORE_PATH: Path = BASE_DIR / "data" / "vectorstore"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / "Chat-bot-project/.env" ,
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

if not settings.OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY not set. Add it to .env or environment variables."
    )
