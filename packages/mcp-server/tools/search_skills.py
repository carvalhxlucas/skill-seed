"""search_skills MCP tool — search the SkillSeed registry."""

from __future__ import annotations

import httpx

from mcp_config import get_http_client


async def search_skills(query: str) -> list[dict]:
    """Search available skills in the SkillSeed network.

    Args:
        query: Text to search for in skill names and descriptions.

    Returns:
        List of matching skill dicts with id, name, description, category.
    """
    async with get_http_client() as client:
        params = {"search": query} if query else {}
        resp = await client.get("/v1/skills/registry", params=params)
        resp.raise_for_status()
        skills = resp.json()

    return [
        {
            "id": s["id"],
            "name": s["name"],
            "description": s["description"],
            "category": s["category"],
            "version": s["version"],
        }
        for s in skills
    ]
