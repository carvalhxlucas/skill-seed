"""Core data models for the SkillSeed protocol."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Skill(BaseModel):
    """A validated capability that an agent can learn."""

    id: str  # e.g. "sql-expert"
    name: str
    description: str
    version: str  # semver
    category: str
    curriculum: list[str]  # tasks the seeder uses to teach
    eval_tasks: list[str]  # tasks used to benchmark the grower

    model_config = {"frozen": False}


class AgentProfile(BaseModel):
    """Profile of an agent enrolled in the SkillSeed network."""

    id: str
    name: str
    framework: str  # "langchain" | "langgraph" | "custom" | etc
    bloomed_skills: list[str] = Field(default_factory=list)  # skill ids

    model_config = {"frozen": False}


class LearningSession(BaseModel):
    """Tracks the progress of a skill transfer from seeder to grower."""

    id: str
    agent_id: str
    skill_id: str
    status: Literal["pending", "learning", "evaluating", "bloomed", "failed"]
    started_at: datetime
    completed_at: datetime | None = None
    eval_score: float | None = None
    learned_state: dict = Field(default_factory=dict)  # system prompt delta, memory injections, etc

    model_config = {"frozen": False}


class SeederProfile(BaseModel):
    """Profile of an agent that teaches a skill to others."""

    id: str
    skill_id: str
    agent_id: str
    reputation_score: float = 0.0  # based on how many agents bloomed
    total_learners: int = 0
    is_root: bool = False  # True = curated by SkillSeed team

    model_config = {"frozen": False}
