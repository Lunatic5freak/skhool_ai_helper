from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root (Chat-bot-project/)
BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/data/chatbot.db"
    VECTORSTORE_PATH: Path = BASE_DIR / "data" / "vectorstore"

    # Explicitly load .env file
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8"
    )

settings = Settings()
