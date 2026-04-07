"""In-memory SkillRegistry — stores and queries available skills."""

from __future__ import annotations

from skillseed_core.models import Skill


class SkillRegistry:
    """In-memory registry of skills available in the SkillSeed network."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        """Add or update a skill in the registry."""
        self._skills[skill.id] = skill

    def get(self, skill_id: str) -> Skill | None:
        """Retrieve a skill by its ID, or None if not found."""
        return self._skills.get(skill_id)

    def search(self, query: str = "", category: str = "") -> list[Skill]:
        """Search skills by text query and/or category.

        - query: matches against skill id, name, and description (case-insensitive)
        - category: exact match against skill.category (case-insensitive)
        """
        results: list[Skill] = []
        query_lower = query.lower()
        category_lower = category.lower()

        for skill in self._skills.values():
            if category_lower and skill.category.lower() != category_lower:
                continue
            if query_lower:
                searchable = f"{skill.id} {skill.name} {skill.description}".lower()
                if query_lower not in searchable:
                    continue
            results.append(skill)

        return results

    def list_all(self) -> list[Skill]:
        """Return all registered skills."""
        return list(self._skills.values())

    def unregister(self, skill_id: str) -> bool:
        """Remove a skill from the registry. Returns True if it existed."""
        if skill_id in self._skills:
            del self._skills[skill_id]
            return True
        return False

    def __len__(self) -> int:
        return len(self._skills)

    def __contains__(self, skill_id: str) -> bool:
        return skill_id in self._skills
