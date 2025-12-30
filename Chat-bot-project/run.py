from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]  # adjust if needed
data_dir = BASE_DIR / "data"
data_dir.mkdir(parents=True, exist_ok=True)

db_file = data_dir / "chatbot.db"
if not db_file.exists():
    db_file.touch()  # create empty sqlite file

print("Database ready at:", db_file)
