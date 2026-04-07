"""Skills router — browse registry and manage learning sessions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from skillseed_core.models import LearningSession, Skill

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
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return session


@router.get("/skills/learn/{session_id}", response_model=LearningSession)
async def get_session(session_id: str, request: Request) -> LearningSession:
    """Poll the status of a learning session."""
    service = request.app.state.learning_service
    session = service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return session


@router.post("/skills/reload", status_code=200)
async def reload_skills(request: Request) -> dict:
    """Re-scan the seeders directory and register any new or updated skills.

    Useful when YAML files are added without restarting the API.
    """
    service = request.app.state.learning_service
    total = service.reload_skills()
    return {"status": "ok", "total_skills": total}
