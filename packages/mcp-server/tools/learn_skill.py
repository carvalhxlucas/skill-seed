"""learn_skill MCP tool — start a learning session."""

from __future__ import annotations

from mcp_config import get_http_client


async def learn_skill(skill_id: str, agent_id: str) -> dict:
    """Start a learning session for the given skill.

    Triggers the PromptDistillationProtocol on the API and returns the
    resulting LearningSession once it reaches a terminal status.

    Args:
        skill_id: ID of the skill to learn (e.g. "sql-expert").
        agent_id: ID of the enrolled agent that will learn.

    Returns:
        LearningSession dict with status, eval_score, and learned_state.
    """
    async with get_http_client() as client:
        resp = await client.post(
            "/v1/skills/learn",
            json={"agent_id": agent_id, "skill_id": skill_id},
        )
        resp.raise_for_status()
        session = resp.json()

    return {
        "session_id": session["id"],
        "agent_id": session["agent_id"],
        "skill_id": session["skill_id"],
        "status": session["status"],
        "eval_score": session.get("eval_score"),
        "learned_state": session.get("learned_state", {}),
        "started_at": session["started_at"],
        "completed_at": session.get("completed_at"),
    }
