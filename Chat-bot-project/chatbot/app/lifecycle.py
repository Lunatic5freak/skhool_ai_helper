from fastapi import FastAPI
from chatbot.app.api import router

def create_app() -> FastAPI:
    app = FastAPI(title="Production AI Chatbot")
    app.include_router(router)
    return app
