from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from .settings import get_settings

settings = get_settings()

from app.db import get_engine

from app.api import hazards, fragilities, mappings, building_datasets, runs

app = FastAPI(title=settings.app_name, debug=settings.LOG_LEVEL == 'DEBUG')

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:  # pragma: no cover
    SQLModel.metadata.create_all(get_engine())


@app.get("/ping")
async def ping() -> dict[str, str]:
    return {"status": "ok"}

for r in (hazards, fragilities, mappings, building_datasets, runs):
    app.include_router(r.router)
    app.include_router(r.router)
    app.include_router(r.router)
    app.include_router(r.router)
    app.include_router(r.router)
