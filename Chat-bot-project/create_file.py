from pathlib import Path


def create_structure():
    base = Path("chatbot")

    # Define all paths
    paths = [
        # App
        base / "app/api.py",
        base / "app/lifecycle.py",
        base / "app/schemas.py",

        # Domain
        base / "domain/agent.py",
        base / "domain/prompts.py",
        base / "domain/policies.py",

        # Infrastructure
        base / "infra/db.py",
        base / "infra/vectorstore.py",
        base / "infra/settings.py",

        # Tools
        base / "tools/sql.py",
        base / "tools/schema.py",
        base / "tools/retrieval.py",

        # Ingestion
        base / "ingestion/ingest_documents.py",

        # Data directories
        base / "data/chatbot.db",
        base / "data/documents",

        # Tests
        base / "tests/__init__.py",
        base / "tests/test_agent.py",
        base / "tests/test_api.py",
        base / "tests/test_tools.py",
    ]

    # Create all directories and files
    for path in paths:
        if path.suffix:  # It's a file
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        else:  # It's a directory
            path.mkdir(parents=True, exist_ok=True)
        print(f"Created: {path}")


if __name__ == "__main__":
    create_structure()
    print("\n✅ Folder structure created successfully!")