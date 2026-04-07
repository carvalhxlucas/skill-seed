"""seed_skill MCP tool — contribute a new skill to the network."""

from __future__ import annotations

import uuid

from mcp_config import get_http_client, get_agent_id


async def seed_skill(
    skill_name: str,
    description: str,
    curriculum: list[str],
) -> dict:
    """Contribute a new skill to the SkillSeed network.

    Registers the calling agent as a seeder for a new skill definition.

    Args:
        skill_name: Human-readable name for the skill (e.g. "SQL Expert").
        description: What this skill teaches and covers.
        curriculum: List of tasks/prompts the seeder uses to teach the skill.

    Returns:
        SeederProfile dict with the new seeder's ID and metadata.
    """
    # Derive a URL-safe skill ID from the name
    skill_id = skill_name.lower().replace(" ", "-").replace("_", "-")

    agent_id = get_agent_id()

    skill_payload = {
        "id": skill_id,
        "name": skill_name,
        "description": description,
        "version": "1.0.0",
        "category": "community",
        "curriculum": curriculum,
        "eval_tasks": [f"Demonstrate: {curriculum[0]}"] if curriculum else [],
    }

    async with get_http_client() as client:
        # Ensure the agent is enrolled (create one if needed)
        try:
            enroll_resp = await client.post(
                "/v1/agents/enroll",
                json={"name": "mcp-agent", "framework": "claude-code"},
            )
            enroll_resp.raise_for_status()
            enrolled_agent_id = enroll_resp.json()["id"]
        except Exception:
            enrolled_agent_id = agent_id

        resp = await client.post(
            "/v1/skills/seed",
            json={"agent_id": enrolled_agent_id, "skill": skill_payload},
        )
        resp.raise_for_status()
        seeder = resp.json()

    return {
        "seeder_id": seeder["id"],
        "skill_id": seeder["skill_id"],
        "agent_id": seeder["agent_id"],
        "is_root": seeder["is_root"],
        "message": f"Successfully registered as seeder for '{skill_name}'.",
    }
