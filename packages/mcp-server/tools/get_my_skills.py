"""get_my_skills MCP tool — list bloomed skills for an agent."""

from __future__ import annotations

from mcp_config import get_http_client


async def get_my_skills(agent_id: str) -> list[dict]:
    """List all bloomed skills for a given agent.

    Args:
        agent_id: ID of the enrolled agent.

    Returns:
        List of skill ID strings the agent has successfully learned.
    """
    async with get_http_client() as client:
        resp = await client.get(f"/v1/agents/{agent_id}/skills")
        resp.raise_for_status()
        skill_ids: list[str] = resp.json()

    return [{"skill_id": sid} for sid in skill_ids]
