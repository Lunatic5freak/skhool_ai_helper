import uvicorn
from app.lifecycle import create_app
from infra.db import init_db

init_db()
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
