"""Agent router — enroll agents and query their skills."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from skillseed_core.models import AgentProfile

router = APIRouter()


class EnrollRequest(BaseModel):
    name: str
    framework: str


@router.post("/agents/enroll", response_model=AgentProfile, status_code=201)
async def enroll_agent(body: EnrollRequest, request: Request) -> AgentProfile:
    """Enroll a new agent in the SkillSeed network."""
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="Agent name must not be empty.")
    if not body.framework.strip():
        raise HTTPException(status_code=422, detail="Agent framework must not be empty.")

    service = request.app.state.learning_service
    agent = service.enroll_agent(name=body.name.strip(), framework=body.framework.strip())
    return agent


@router.get("/agents/{agent_id}/skills", response_model=list[str])
async def get_agent_skills(agent_id: str, request: Request) -> list[str]:
    """Return the list of bloomed skill IDs for an agent."""
    service = request.app.state.learning_service
    agent = service.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")
    return agent.bloomed_skills


@router.get("/agents/{agent_id}", response_model=AgentProfile)
async def get_agent(agent_id: str, request: Request) -> AgentProfile:
    """Return an agent's full profile."""
    service = request.app.state.learning_service
    agent = service.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")
    return agent
