"""Seeders router — feedback signals and curriculum evolution."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from skillseed_core.models import CurriculumVersion, FeedbackSignal

router = APIRouter()


class EvolveRequest(BaseModel):
    force: bool = False


@router.get("/seeders/{seeder_id}/feedback", response_model=list[FeedbackSignal])
async def get_seeder_feedback(
    seeder_id: str,
    request: Request,
    last_n: int = Query(default=50, ge=1, le=500),
) -> list[FeedbackSignal]:
    """Return feedback signals for a seeder.

    Only public eval data is included — shadow_eval_score is never exposed.
    """
    service = request.app.state.learning_service
    seeder = service.get_seeder(seeder_id)
    if seeder is None:
        raise HTTPException(status_code=404, detail="Seeder not found.")

    evolution_service = request.app.state.evolution_service
    return evolution_service.get_signals(seeder_id=seeder_id, last_n=last_n)


@router.get("/seeders/{seeder_id}/curriculum/history", response_model=list[CurriculumVersion])
async def get_curriculum_history(seeder_id: str, request: Request) -> list[CurriculumVersion]:
    """Return the full curriculum revision history for a seeder."""
    service = request.app.state.learning_service
    seeder = service.get_seeder(seeder_id)
    if seeder is None:
        raise HTTPException(status_code=404, detail="Seeder not found.")

    evolution_service = request.app.state.evolution_service
    return evolution_service.get_curriculum_history(seeder_id=seeder_id)


@router.post("/seeders/{seeder_id}/evolve", response_model=CurriculumVersion | None)
async def evolve_seeder(
    seeder_id: str,
    body: EvolveRequest,
    request: Request,
) -> CurriculumVersion | None:
    """Trigger a curriculum revision for a seeder.

    If force=true, bypasses the minimum signal threshold and revises immediately.
    Returns the new CurriculumVersion, or null if no revision was needed.
    """
    learning_service = request.app.state.learning_service
    seeder = learning_service.get_seeder(seeder_id)
    if seeder is None:
        raise HTTPException(status_code=404, detail="Seeder not found.")

    skill = learning_service.get_registry().get(seeder.skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill for this seeder not found.")

    evolution_service = request.app.state.evolution_service
    version = await evolution_service.evolve(seeder=seeder, skill=skill, force=body.force)
    return version
