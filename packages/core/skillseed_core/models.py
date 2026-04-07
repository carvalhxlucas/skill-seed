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
    curriculum: list[str] = Field(..., max_length=50)
    eval_tasks: list[str] = Field(..., max_length=50)
    # Shadow eval tasks — NEVER exposed in public API responses.
    # Anti-gaming protection: seeders never see these tasks, preventing teaching-to-the-test.
    shadow_eval_tasks: list[str] = Field(default_factory=list, max_length=20)

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
    bloomed_skills: list[str] = Field(default_factory=list)

    model_config = {"frozen": False}


class LearningSession(BaseModel):
    """Tracks the progress of a skill transfer from seeder to grower."""

    id: str
    agent_id: str
    skill_id: str
    seeder_id: str = ""
    status: Literal["pending", "learning", "evaluating", "bloomed", "failed"]
    started_at: datetime
    completed_at: datetime | None = None
    eval_score: float | None = None
    # Shadow eval score — NEVER sent to seeders. Used internally to detect score inflation.
    shadow_eval_score: float | None = None
    # Tasks the grower failed during the public eval — included in FeedbackSignal.
    failed_tasks: list[str] = Field(default_factory=list)
    learned_state: dict = Field(default_factory=dict)

    model_config = {"frozen": False}


class FeedbackSignal(BaseModel):
    """Feedback sent to a seeder after a learning session completes.

    Contains only public eval data. shadow_eval_score is NEVER included.
    """

    id: str
    seeder_id: str
    skill_id: str
    session_id: str
    eval_score: float               # public score only — shadow score never sent
    failed_tasks: list[str] = Field(default_factory=list)
    grower_responses: dict = Field(default_factory=dict)
    created_at: datetime

    model_config = {"frozen": False}


class CurriculumVersion(BaseModel):
    """A versioned snapshot of a seeder's curriculum after a revision."""

    id: str
    skill_id: str
    seeder_id: str
    version: str                    # semver — bumped on each revision
    curriculum: list[str]
    revision_reason: str
    avg_bloom_rate: float | None = None
    created_at: datetime

    model_config = {"frozen": False}

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        if not _SEMVER_RE.match(v):
            raise ValueError("version must follow semver format")
        return v


class SeederProfile(BaseModel):
    """Profile of an agent that teaches a skill to others."""

    id: str
    skill_id: str
    agent_id: str
    reputation_score: float = 0.0
    total_learners: int = 0
    bloom_rate: float = 0.0         # % of growers who bloomed with this seeder
    curriculum_version: str = "1.0.0"
    is_root: bool = False
    evolution_enabled: bool = False  # whether this seeder auto-revises curriculum

    model_config = {"frozen": False}
