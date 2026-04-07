"""Seed router — register agents as skill seeders."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from skillseed_core.models import Skill, SeederProfile

router = APIRouter()


class SeedRequest(BaseModel):
    agent_id: str
    skill: Skill


@router.post("/skills/seed", response_model=SeederProfile, status_code=201)
async def seed_skill(body: SeedRequest, request: Request) -> SeederProfile:
    """Register an agent as a seeder for a given skill.

    The skill will be added to the registry if it doesn't exist yet.
    """
    service = request.app.state.learning_service
    try:
        seeder = service.register_seeder(
            agent_id=body.agent_id,
            skill=body.skill,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return seeder
