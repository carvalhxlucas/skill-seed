"""SkillSeed REST API — FastAPI application entrypoint."""

from __future__ import annotations

import os
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from routers import agents, skills, seed, seeders
from services.learning_service import LearningService
from services.eval_service import EvalService
from services.evolution_service import EvolutionService

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_API_KEY = os.environ.get("SKILLSEED_API_KEY", "")
_ENABLE_DOCS = os.environ.get("ENABLE_DOCS", "false").lower() == "true"
_CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]

# Paths that are always public (no API key required)
_PUBLIC_PATHS = {"/", "/health"}
if _ENABLE_DOCS:
    _PUBLIC_PATHS |= {"/docs", "/redoc", "/openapi.json"}


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """M-3: inject security headers on every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize shared services on startup."""
    app.state.learning_service = LearningService()
    app.state.eval_service = EvalService()
    app.state.evolution_service = EvolutionService()
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SkillSeed API",
    description="Open network where AI agents teach and learn skills from each other.",
    version="0.1.0",
    lifespan=lifespan,
    # M-3: disable interactive docs by default; enable via ENABLE_DOCS=true
    docs_url="/docs" if _ENABLE_DOCS else None,
    redoc_url="/redoc" if _ENABLE_DOCS else None,
    openapi_url="/openapi.json" if _ENABLE_DOCS else None,
)

# M-3: security headers on all responses
app.add_middleware(SecurityHeadersMiddleware)

# A-2: CORS — no wildcard with credentials; origins must be explicitly listed
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)


# A-1: API key authentication on all non-public routes
@app.middleware("http")
async def require_api_key(request: Request, call_next):
    if request.url.path in _PUBLIC_PATHS:
        return await call_next(request)

    if not _API_KEY:
        # No key configured → open mode (dev only); warn but allow
        return await call_next(request)

    provided = request.headers.get("X-API-Key", "")
    # secrets.compare_digest prevents timing attacks
    if not provided or not secrets.compare_digest(provided.encode(), _API_KEY.encode()):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid or missing API key."},
        )
    return await call_next(request)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(agents.router, prefix="/v1", tags=["agents"])
app.include_router(skills.router, prefix="/v1", tags=["skills"])
app.include_router(seed.router, prefix="/v1", tags=["seed"])
app.include_router(seeders.router, prefix="/v1", tags=["seeders"])


@app.get("/", tags=["health"])
async def root() -> dict:
    return {"service": "skillseed-api", "version": "0.1.0", "status": "ok"}


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
