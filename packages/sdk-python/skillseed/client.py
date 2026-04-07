"""SkillSeed Python SDK — main client entrypoint."""

from __future__ import annotations

import httpx

from skillseed_core.models import AgentProfile, Skill, SeederProfile
from .agent import EnrolledAgent
from .registry import RegistryClient


class SkillSeed:
    """Main entrypoint for the SkillSeed Python SDK.

    Usage::

        from skillseed import SkillSeed

        ss = SkillSeed(api_key="sk-...")
        agent = ss.enroll(name="my-assistant", framework="langchain")
        session = agent.learn("sql-expert")
        print(session.status)  # "bloomed"
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(
            base_url=self.base_url,
            headers={
                "X-API-Key": api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=timeout,
        )
        self.registry = RegistryClient(self._http)

    def enroll(self, name: str, framework: str) -> EnrolledAgent:
        """Enroll a new agent and return an EnrolledAgent handle.

        Args:
            name: Display name for the agent.
            framework: Agent framework (e.g. "langchain", "langgraph", "custom").

        Returns:
            EnrolledAgent ready to call .learn() and .seed().
        """
        resp = self._http.post(
            "/v1/agents/enroll",
            json={"name": name, "framework": framework},
        )
        resp.raise_for_status()
        profile = AgentProfile.model_validate(resp.json())
        return EnrolledAgent(profile=profile, client=self._http)

    def get_agent(self, agent_id: str) -> EnrolledAgent:
        """Retrieve an existing enrolled agent by ID."""
        resp = self._http.get(f"/v1/agents/{agent_id}")
        resp.raise_for_status()
        profile = AgentProfile.model_validate(resp.json())
        return EnrolledAgent(profile=profile, client=self._http)

    def seed(self, agent_id: str, skill: Skill) -> SeederProfile:
        """Register an agent as a seeder for a given skill.

        Args:
            agent_id: ID of the enrolled agent that will seed.
            skill: The Skill definition to contribute.

        Returns:
            SeederProfile for the registered seeder.
        """
        resp = self._http.post(
            "/v1/skills/seed",
            json={"agent_id": agent_id, "skill": skill.model_dump()},
        )
        resp.raise_for_status()
        return SeederProfile.model_validate(resp.json())

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._http.close()

    def __enter__(self) -> "SkillSeed":
        return self

    def __exit__(self, *args) -> None:
        self.close()
