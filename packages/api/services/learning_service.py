"""LearningService — orchestrates the SkillSeed protocol and manages session state."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from skillseed_core.models import AgentProfile, LearningSession, Skill, SeederProfile
from skillseed_core.protocol import PromptDistillationProtocol
from skillseed_core.registry import SkillRegistry
from skillseed_core.eval import SimpleEvaluator
from services.yaml_loader import load_skills_from_directory, persist_skill_to_yaml


class LearningService:
    """Orchestrates skill transfer sessions.

    Uses in-memory storage for MVP. Replace with Redis/PostgreSQL for production.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, LearningSession] = {}
        self._agents: dict[str, AgentProfile] = {}
        self._seeders: dict[str, SeederProfile] = {}
        self._registry = SkillRegistry()
        self._protocol = PromptDistillationProtocol(threshold=0.7)

        self._load_skills_from_yaml()

    def _load_skills_from_yaml(self) -> None:
        """Load all skills from the seeders YAML directory."""
        for skill in load_skills_from_directory():
            self._registry.register(skill)

    def reload_skills(self) -> int:
        """Re-scan the seeders directory and register any new or updated skills.

        Returns the total number of skills now in the registry.
        """
        for skill in load_skills_from_directory():
            self._registry.register(skill)
        return len(self._registry)

    # ------------------------------------------------------------------
    # Agent management
    # ------------------------------------------------------------------

    def enroll_agent(self, name: str, framework: str) -> AgentProfile:
        """Create and store a new agent profile."""
        agent = AgentProfile(
            id=str(uuid.uuid4()),
            name=name,
            framework=framework,
            bloomed_skills=[],
        )
        self._agents[agent.id] = agent
        return agent

    def get_agent(self, agent_id: str) -> AgentProfile | None:
        return self._agents.get(agent_id)

    def get_agent_skills(self, agent_id: str) -> list[str]:
        agent = self._agents.get(agent_id)
        if not agent:
            return []
        return agent.bloomed_skills

    # ------------------------------------------------------------------
    # Skill registry
    # ------------------------------------------------------------------

    def get_registry(self) -> SkillRegistry:
        return self._registry

    def register_skill(self, skill: Skill) -> None:
        self._registry.register(skill)

    # ------------------------------------------------------------------
    # Learning sessions
    # ------------------------------------------------------------------

    async def start_learning(self, agent_id: str, skill_id: str) -> LearningSession:
        """Start a new learning session for the given agent and skill."""
        agent = self._agents.get(agent_id)
        if agent is None:
            raise ValueError(f"Agent '{agent_id}' not found. Enroll the agent first.")

        skill = self._registry.get(skill_id)
        if skill is None:
            raise ValueError(f"Skill '{skill_id}' not found in registry.")

        # Create a root seeder for built-in skills
        seeder = self._get_or_create_root_seeder(skill)
        session = await self._protocol.transfer(skill, seeder, agent)

        # Update seeder stats
        seeder.total_learners += 1
        if session.status == "bloomed":
            bloomed_count = sum(
                1 for s in self._sessions.values()
                if s.skill_id == skill_id and s.status == "bloomed"
            ) + 1
            seeder.bloom_rate = round(bloomed_count / seeder.total_learners, 3)

        self._sessions[session.id] = session
        return session

    def _get_or_create_root_seeder(self, skill: Skill) -> SeederProfile:
        """Return or create the root seeder for a built-in skill."""
        root_id = f"root-{skill.id}"
        if root_id not in self._seeders:
            self._seeders[root_id] = SeederProfile(
                id=root_id,
                skill_id=skill.id,
                agent_id="skillseed-root",
                reputation_score=5.0,
                total_learners=0,
                bloom_rate=0.0,
                curriculum_version=skill.version,
                is_root=True,
                evolution_enabled=True,
            )
        return self._seeders[root_id]

    def get_session(self, session_id: str) -> LearningSession | None:
        return self._sessions.get(session_id)

    # ------------------------------------------------------------------
    # Seeder management
    # ------------------------------------------------------------------

    def register_seeder(self, agent_id: str, skill: Skill) -> SeederProfile:
        """Register an agent as a seeder for a given skill.

        If the skill is new, it is persisted as a YAML file so it survives
        restarts and is immediately discoverable by other agents.
        """
        if agent_id not in self._agents:
            raise ValueError(f"Agent '{agent_id}' not found. Enroll the agent first.")

        # Register the skill and persist it to disk if it's new
        if self._registry.get(skill.id) is None:
            self._registry.register(skill)
            persist_skill_to_yaml(skill)

        seeder = SeederProfile(
            id=str(uuid.uuid4()),
            skill_id=skill.id,
            agent_id=agent_id,
            reputation_score=0.0,
            total_learners=0,
            bloom_rate=0.0,
            curriculum_version=skill.version,
            is_root=False,
            evolution_enabled=False,
        )
        self._seeders[seeder.id] = seeder
        return seeder

    def get_seeder(self, seeder_id: str) -> SeederProfile | None:
        return self._seeders.get(seeder_id)
