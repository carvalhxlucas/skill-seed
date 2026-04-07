"""Skills router — browse registry and manage learning sessions."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from skillseed_core.models import LearningSession, Skill

# A-3: admin key for privileged endpoints (reload)
_ADMIN_KEY = os.environ.get("SKILLSEED_ADMIN_KEY", os.environ.get("SKILLSEED_API_KEY", ""))
_admin_key_scheme = APIKeyHeader(name="X-Admin-Key", auto_error=False)


async def require_admin_key(key: str | None = Depends(_admin_key_scheme)) -> None:
    """Dependency that enforces admin key for privileged operations."""
    import secrets
    if not _ADMIN_KEY:
        return  # dev mode — no key configured
    if not key or not secrets.compare_digest(key.encode(), _ADMIN_KEY.encode()):
        raise HTTPException(status_code=403, detail="Admin access required.")

router = APIRouter()


class LearnRequest(BaseModel):
    agent_id: str
    skill_id: str


@router.get("/skills/registry", response_model=list[Skill])
async def get_registry(
    request: Request,
    category: str = Query(default="", description="Filter by category"),
    search: str = Query(default="", description="Search by name/description"),
) -> list[Skill]:
    """Return available skills, optionally filtered by category and/or search query."""
    service = request.app.state.learning_service
    registry = service.get_registry()
    return registry.search(query=search, category=category)


@router.post("/skills/learn", response_model=LearningSession, status_code=201)
async def start_learning(body: LearnRequest, request: Request) -> LearningSession:
    """Start a learning session — triggers the PromptDistillationProtocol."""
    service = request.app.state.learning_service
    try:
        session = await service.start_learning(
            agent_id=body.agent_id,
            skill_id=body.skill_id,
        )
    except ValueError:
        # M-2: do not leak internal error messages
        raise HTTPException(status_code=404, detail="Agent or skill not found.")
    return session


@router.get("/skills/learn/{session_id}", response_model=LearningSession)
async def get_session(session_id: str, request: Request) -> LearningSession:
    """Poll the status of a learning session."""
    service = request.app.state.learning_service
    session = service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session


@router.post("/skills/reload", status_code=200, dependencies=[Depends(require_admin_key)])
async def reload_skills(request: Request) -> dict:
    """Re-scan the seeders directory and register any new or updated skills.

    Requires X-Admin-Key header (A-3: privileged endpoint).
    """
    service = request.app.state.learning_service
    total = service.reload_skills()
    return {"status": "ok", "total_skills": total}
