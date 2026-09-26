"""
Pipeline Autopilot — FastAPI application entry point.

Registers:
  - CORS middleware (all origins in dev; tighten for production)
  - lifespan: opens DB + creates schema on startup, closes on shutdown
  - API routers: /api/ingest, /api/pipeline, /api/scenarios
  - /health endpoint for Docker healthcheck
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ingest, pipeline, report, scenarios, stream
from app.db.database import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Pipeline Autopilot",
        description="Causal Replay for CI/CD — investigation and recovery engine",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(ingest.router, prefix="/api")
    app.include_router(pipeline.router, prefix="/api")
    app.include_router(scenarios.router, prefix="/api")
    app.include_router(stream.router, prefix="/api")
    app.include_router(report.router, prefix="/api")

    @app.get("/health", tags=["ops"])
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
