from fastapi import FastAPI

from app.core.config import settings
from app.db.sessions import engine
from app.db.base import Base
from app.db import models  
from app.api.repositories import router as repositories_router

print(f"DEBUG: repositories_router imported: {repositories_router}")

def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    @app.on_event("startup")
    async def on_startup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok"}

    app.include_router(repositories_router)
    return app  

app = create_app()