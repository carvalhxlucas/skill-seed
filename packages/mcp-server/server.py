"""SkillSeed MCP Server — FastMCP server exposing SkillSeed tools to Claude Code."""

from __future__ import annotations

import os
import re
import asyncio
from pathlib import Path

from fastmcp import FastMCP

from mcp_config import get_http_client
from tools.search_skills import search_skills as _search_skills
from tools.learn_skill import learn_skill as _learn_skill
from tools.get_my_skills import get_my_skills as _get_my_skills
from tools.seed_skill import seed_skill as _seed_skill

mcp = FastMCP("SkillSeed")


# ---------------------------------------------------------------------------
# Tool registrations
# ---------------------------------------------------------------------------

@mcp.tool()
async def search_skills(query: str) -> list[dict]:
    """Search available skills in the SkillSeed network.

    Args:
        query: Text to search for in skill names and descriptions.

    Returns:
        List of matching skills with id, name, description, category.
    """
    return await _search_skills(query)


@mcp.tool()
async def learn_skill(skill_id: str, agent_id: str) -> dict:
    """Start a learning session for the given skill.

    Args:
        skill_id: ID of the skill to learn (e.g. "sql-expert").
        agent_id: ID of the enrolled agent that will learn.

    Returns:
        LearningSession result with status and learned_state.
    """
    return await _learn_skill(skill_id, agent_id)


@mcp.tool()
async def get_my_skills(agent_id: str) -> list[dict]:
    """List all bloomed skills for a given agent.

    Args:
        agent_id: ID of the enrolled agent.

    Returns:
        List of skill IDs the agent has successfully learned.
    """
    return await _get_my_skills(agent_id)


@mcp.tool()
async def seed_skill(
    skill_name: str,
    description: str,
    curriculum: list[str],
) -> dict:
    """Contribute a new skill to the SkillSeed network.

    Args:
        skill_name: Human-readable name (e.g. "SQL Expert").
        description: What this skill teaches and covers.
        curriculum: List of tasks/prompts used to teach the skill.

    Returns:
        SeederProfile confirming the new seeder registration.
    """
    return await _seed_skill(skill_name, description, curriculum)


# ---------------------------------------------------------------------------
# SKILL_SEED.md auto-detection
# ---------------------------------------------------------------------------

def _parse_skill_seed_md(path: Path) -> list[str]:
    """Parse skill IDs from a SKILL_SEED.md file.

    Looks for lines matching patterns like:
    - `skill: sql-expert`
    - `- sql-expert`
    - `learn: sql-expert`

    Returns a deduplicated list of skill IDs.
    """
    content = path.read_text(encoding="utf-8")
    skill_ids: list[str] = []

    # Match YAML-style "skill: <id>" or "learn: <id>" entries
    patterns = [
        r"^\s*skill:\s*([a-z0-9][a-z0-9\-]*[a-z0-9])\s*$",
        r"^\s*learn:\s*([a-z0-9][a-z0-9\-]*[a-z0-9])\s*$",
        r"^\s*-\s*([a-z0-9][a-z0-9\-]*[a-z0-9])\s*$",
    ]

    for line in content.splitlines():
        for pattern in patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                skill_id = match.group(1).lower()
                if skill_id not in skill_ids:
                    skill_ids.append(skill_id)
                break

    return skill_ids


async def _auto_learn_from_skill_seed_md(agent_id: str) -> None:
    """Check for SKILL_SEED.md in cwd and auto-learn declared skills."""
    cwd = Path.cwd()
    skill_seed_path = cwd / "SKILL_SEED.md"

    if not skill_seed_path.exists():
        return

    print(f"[SkillSeed] Found SKILL_SEED.md at {skill_seed_path}")
    skill_ids = _parse_skill_seed_md(skill_seed_path)

    if not skill_ids:
        print("[SkillSeed] No skill IDs found in SKILL_SEED.md")
        return

    print(f"[SkillSeed] Auto-learning {len(skill_ids)} skill(s): {', '.join(skill_ids)}")

    for skill_id in skill_ids:
        try:
            result = await _learn_skill(skill_id=skill_id, agent_id=agent_id)
            status = result.get("status", "unknown")
            print(f"[SkillSeed] {skill_id}: {status}")
        except Exception as exc:
            print(f"[SkillSeed] Failed to learn '{skill_id}': {exc}")


async def _startup() -> None:
    """Run startup tasks: enroll the MCP agent and process SKILL_SEED.md."""
    agent_id_env = os.environ.get("SKILLSEED_AGENT_ID")

    if not agent_id_env:
        # Try to enroll a new agent for this session
        try:
            async with get_http_client() as client:
                resp = await client.post(
                    "/v1/agents/enroll",
                    json={"name": "claude-code-mcp", "framework": "claude-code"},
                )
                resp.raise_for_status()
                agent_id = resp.json()["id"]
                os.environ["SKILLSEED_AGENT_ID"] = agent_id
                print(f"[SkillSeed] Enrolled MCP agent: {agent_id}")
        except Exception as exc:
            print(f"[SkillSeed] Could not enroll agent (API may be offline): {exc}")
            return
    else:
        agent_id = agent_id_env

    await _auto_learn_from_skill_seed_md(agent_id)


if __name__ == "__main__":
    # Run startup in background, then start the MCP server
    asyncio.run(_startup())
    mcp.run()
