"""RegistryClient — browse the SkillSeed skill registry via the REST API."""

from __future__ import annotations

import httpx

from skillseed_core.models import Skill


class RegistryClient:
    """Client for the /v1/skills/registry endpoint.

    Obtained via ``SkillSeed.registry``::

        ss = SkillSeed(api_key="sk-...")
        skills = ss.registry.search("data")
    """

    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def search(self, query: str = "", category: str = "") -> list[Skill]:
        """Search the registry by query string and/or category.

        Args:
            query: Text to match against skill name/description.
            category: Exact category filter (e.g. "data", "automation").

        Returns:
            List of matching Skill objects.
        """
        params: dict[str, str] = {}
        if query:
            params["search"] = query
        if category:
            params["category"] = category

        resp = self._http.get("/v1/skills/registry", params=params)
        resp.raise_for_status()
        return [Skill.model_validate(s) for s in resp.json()]

    def list(self) -> list[Skill]:
        """Return all available skills in the registry."""
        resp = self._http.get("/v1/skills/registry")
        resp.raise_for_status()
        return [Skill.model_validate(s) for s in resp.json()]

    def get(self, skill_id: str) -> Skill | None:
        """Fetch a specific skill by ID, or None if not found.

        Note: Uses search under the hood since there's no dedicated GET /skills/{id} endpoint.
        """
        results = self.search(query=skill_id)
        for skill in results:
            if skill.id == skill_id:
                return skill
        return None
