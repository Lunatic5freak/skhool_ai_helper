from sqlalchemy import create_engine, text
from chatbot.infra.settings import settings

engine = create_engine(settings.DATABASE_URL)

def init_db():
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            created_at TEXT
        )
        """))
