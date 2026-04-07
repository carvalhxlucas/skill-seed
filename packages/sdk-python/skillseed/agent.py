"""EnrolledAgent — an agent handle with .learn() and .seed() methods."""

from __future__ import annotations

import time

import httpx

from skillseed_core.models import AgentProfile, LearningSession, Skill, SeederProfile


# Terminal statuses — polling stops when these are reached
_TERMINAL_STATUSES = {"bloomed", "failed"}


class EnrolledAgent:
    """Handle for an agent enrolled in the SkillSeed network.

    Obtained via ``SkillSeed.enroll()`` or ``SkillSeed.get_agent()``.
    """

    def __init__(self, profile: AgentProfile, client: httpx.Client) -> None:
        self._profile = profile
        self._http = client

    @property
    def id(self) -> str:
        return self._profile.id

    @property
    def name(self) -> str:
        return self._profile.name

    @property
    def framework(self) -> str:
        return self._profile.framework

    @property
    def profile(self) -> AgentProfile:
        return self._profile

    def learn(
        self,
        skill_id: str,
        poll_interval: float = 0.5,
        timeout: float = 60.0,
    ) -> LearningSession:
        """Start a learning session for ``skill_id`` and block until complete.

        Polls ``GET /v1/skills/learn/{session_id}`` until a terminal status
        ("bloomed" or "failed") is reached.

        Args:
            skill_id: ID of the skill to learn (e.g. "sql-expert").
            poll_interval: Seconds between status polls.
            timeout: Maximum seconds to wait before raising TimeoutError.

        Returns:
            LearningSession with final status and learned_state.

        Raises:
            TimeoutError: If the session doesn't complete within ``timeout``.
        """
        resp = self._http.post(
            "/v1/skills/learn",
            json={"agent_id": self.id, "skill_id": skill_id},
        )
        resp.raise_for_status()
        session = LearningSession.model_validate(resp.json())

        # Poll until terminal
        deadline = time.monotonic() + timeout
        while session.status not in _TERMINAL_STATUSES:
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"Learning session '{session.id}' did not complete within {timeout}s."
                )
            time.sleep(poll_interval)
            poll_resp = self._http.get(f"/v1/skills/learn/{session.id}")
            poll_resp.raise_for_status()
            session = LearningSession.model_validate(poll_resp.json())

        # Refresh local profile skills
        self._refresh_profile()
        return session

    def my_skills(self) -> list[str]:
        """Return the list of bloomed skill IDs for this agent."""
        resp = self._http.get(f"/v1/agents/{self.id}/skills")
        resp.raise_for_status()
        skills: list[str] = resp.json()
        self._profile.bloomed_skills = skills
        return skills

    def seed(self, skill: Skill) -> SeederProfile:
        """Register this agent as a seeder for the given skill.

        Convenience wrapper — also accessible via ``SkillSeed.seed()``.
        """
        resp = self._http.post(
            "/v1/skills/seed",
            json={"agent_id": self.id, "skill": skill.model_dump()},
        )
        resp.raise_for_status()
        return SeederProfile.model_validate(resp.json())

    def _refresh_profile(self) -> None:
        """Refresh the local agent profile from the API."""
        try:
            resp = self._http.get(f"/v1/agents/{self.id}")
            if resp.status_code == 200:
                self._profile = AgentProfile.model_validate(resp.json())
        except httpx.HTTPError:
            pass  # Best-effort refresh

    def __repr__(self) -> str:
        return f"EnrolledAgent(id={self.id!r}, name={self.name!r}, framework={self.framework!r})"
