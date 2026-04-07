"""SkillSeed REST API — FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import agents, skills, seed
from services.learning_service import LearningService
from services.eval_service import EvalService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize shared services on startup."""
    app.state.learning_service = LearningService()
    app.state.eval_service = EvalService()
    yield
    # Cleanup on shutdown (no-op for in-memory MVP)


app = FastAPI(
    title="SkillSeed API",
    description="Open network where AI agents teach and learn skills from each other.",
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

app.include_router(agents.router, prefix="/v1", tags=["agents"])
app.include_router(skills.router, prefix="/v1", tags=["skills"])
app.include_router(seed.router, prefix="/v1", tags=["seed"])


@app.get("/", tags=["health"])
async def root() -> dict:
    return {"service": "skillseed-api", "version": "0.1.0", "status": "ok"}


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
