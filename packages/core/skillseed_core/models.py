"""Core data models for the SkillSeed protocol."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# C-1 / M-1: only lowercase alphanumeric and hyphens, 3-64 chars, no leading/trailing hyphen
_SKILL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{1,62}[a-z0-9]$")
# B-1: semver with optional pre-release label
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9\.]+)?$")


class Skill(BaseModel):
    """A validated capability that an agent can learn."""

    id: str  # e.g. "sql-expert"
    name: str = Field(..., max_length=100)
    description: str = Field(..., max_length=2000)
    version: str  # semver
    category: str = Field(..., max_length=64)
    curriculum: list[str] = Field(..., max_length=50)   # A-4: cap list size
    eval_tasks: list[str] = Field(..., max_length=50)   # A-4: cap list size

    model_config = {"frozen": False}

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """C-1 / M-1: reject IDs that could cause path traversal or registry pollution."""
        if not _SKILL_ID_RE.match(v):
            raise ValueError(
                "Skill ID must be 3-64 characters, lowercase alphanumeric and hyphens only, "
                "and cannot start or end with a hyphen."
            )
        return v

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """B-1: enforce semver format."""
        if not _SEMVER_RE.match(v):
            raise ValueError("version must follow semver format (e.g. 1.0.0 or 1.0.0-beta.1)")
        return v


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
