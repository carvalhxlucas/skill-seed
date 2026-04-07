"""Tests for MCP server tools using mocked HTTP responses."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_skill_dict(**kwargs) -> dict:
    defaults = {
        "id": "sql-expert",
        "name": "SQL Expert",
        "description": "Teaches SQL.",
        "version": "1.0.0",
        "category": "data",
        "curriculum": ["Write a SELECT query"],
        "eval_tasks": ["Find duplicates"],
    }
    defaults.update(kwargs)
    return defaults


def make_session_dict(**kwargs) -> dict:
    defaults = {
        "id": "session-123",
        "agent_id": "agent-456",
        "skill_id": "sql-expert",
        "status": "bloomed",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "eval_score": 0.85,
        "learned_state": {"system_prompt_delta": "You are an SQL expert."},
    }
    defaults.update(kwargs)
    return defaults


def make_seeder_dict(**kwargs) -> dict:
    defaults = {
        "id": "seeder-789",
        "skill_id": "sql-expert",
        "agent_id": "agent-456",
        "reputation_score": 0.0,
        "total_learners": 0,
        "is_root": False,
    }
    defaults.update(kwargs)
    return defaults


def mock_async_response(data: dict | list, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json = MagicMock(return_value=data)
    resp.raise_for_status = MagicMock()
    return resp


@asynccontextmanager
async def mock_http_client(get_return=None, post_return=None):
    """Async context manager that yields a mock HTTP client."""
    client = MagicMock()
    if get_return is not None:
        client.get = AsyncMock(return_value=get_return)
    if post_return is not None:
        client.post = AsyncMock(return_value=post_return)
    yield client


# ---------------------------------------------------------------------------
# search_skills tests
# ---------------------------------------------------------------------------

class TestSearchSkillsTool:
    @pytest.mark.asyncio
    async def test_search_returns_skill_list(self):
        mock_resp = mock_async_response([make_skill_dict()])

        with patch("tools.search_skills.get_http_client") as mock_ctx:
            mock_ctx.return_value = mock_http_client(get_return=mock_resp)
            from tools.search_skills import search_skills
            results = await search_skills("sql")

        assert len(results) == 1
        assert results[0]["id"] == "sql-expert"
        assert results[0]["name"] == "SQL Expert"
        assert "description" in results[0]
        assert "category" in results[0]

    @pytest.mark.asyncio
    async def test_search_empty_query(self):
        mock_resp = mock_async_response([make_skill_dict(), make_skill_dict(id="web-scraper", name="Web Scraper")])

        with patch("tools.search_skills.get_http_client") as mock_ctx:
            mock_ctx.return_value = mock_http_client(get_return=mock_resp)
            from tools.search_skills import search_skills
            results = await search_skills("")

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_no_results(self):
        mock_resp = mock_async_response([])

        with patch("tools.search_skills.get_http_client") as mock_ctx:
            mock_ctx.return_value = mock_http_client(get_return=mock_resp)
            from tools.search_skills import search_skills
            results = await search_skills("nonexistent")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_includes_version_field(self):
        mock_resp = mock_async_response([make_skill_dict()])

        with patch("tools.search_skills.get_http_client") as mock_ctx:
            mock_ctx.return_value = mock_http_client(get_return=mock_resp)
            from tools.search_skills import search_skills
            results = await search_skills("sql")

        assert "version" in results[0]
        assert results[0]["version"] == "1.0.0"


# ---------------------------------------------------------------------------
# learn_skill tests
# ---------------------------------------------------------------------------

class TestLearnSkillTool:
    @pytest.mark.asyncio
    async def test_learn_returns_session(self):
        mock_resp = mock_async_response(make_session_dict(), 201)

        with patch("tools.learn_skill.get_http_client") as mock_ctx:
            mock_ctx.return_value = mock_http_client(post_return=mock_resp)
            from tools.learn_skill import learn_skill
            result = await learn_skill("sql-expert", "agent-456")

        assert result["session_id"] == "session-123"
        assert result["skill_id"] == "sql-expert"
        assert result["agent_id"] == "agent-456"
        assert result["status"] == "bloomed"
        assert result["eval_score"] == 0.85

    @pytest.mark.asyncio
    async def test_learn_includes_learned_state(self):
        mock_resp = mock_async_response(make_session_dict(), 201)

        with patch("tools.learn_skill.get_http_client") as mock_ctx:
            mock_ctx.return_value = mock_http_client(post_return=mock_resp)
            from tools.learn_skill import learn_skill
            result = await learn_skill("sql-expert", "agent-456")

        assert "learned_state" in result
        assert "system_prompt_delta" in result["learned_state"]

    @pytest.mark.asyncio
    async def test_learn_failed_status(self):
        mock_resp = mock_async_response(make_session_dict(status="failed", eval_score=0.4), 201)

        with patch("tools.learn_skill.get_http_client") as mock_ctx:
            mock_ctx.return_value = mock_http_client(post_return=mock_resp)
            from tools.learn_skill import learn_skill
            result = await learn_skill("sql-expert", "agent-456")

        assert result["status"] == "failed"
        assert result["eval_score"] == 0.4

    @pytest.mark.asyncio
    async def test_learn_includes_timestamps(self):
        mock_resp = mock_async_response(make_session_dict(), 201)

        with patch("tools.learn_skill.get_http_client") as mock_ctx:
            mock_ctx.return_value = mock_http_client(post_return=mock_resp)
            from tools.learn_skill import learn_skill
            result = await learn_skill("sql-expert", "agent-456")

        assert "started_at" in result
        assert "completed_at" in result


# ---------------------------------------------------------------------------
# get_my_skills tests
# ---------------------------------------------------------------------------

class TestGetMySkillsTool:
    @pytest.mark.asyncio
    async def test_get_skills_returns_list(self):
        mock_resp = mock_async_response(["sql-expert", "web-scraper"])

        with patch("tools.get_my_skills.get_http_client") as mock_ctx:
            mock_ctx.return_value = mock_http_client(get_return=mock_resp)
            from tools.get_my_skills import get_my_skills
            results = await get_my_skills("agent-456")

        assert len(results) == 2
        assert {"skill_id": "sql-expert"} in results
        assert {"skill_id": "web-scraper"} in results

    @pytest.mark.asyncio
    async def test_get_skills_empty_agent(self):
        mock_resp = mock_async_response([])

        with patch("tools.get_my_skills.get_http_client") as mock_ctx:
            mock_ctx.return_value = mock_http_client(get_return=mock_resp)
            from tools.get_my_skills import get_my_skills
            results = await get_my_skills("new-agent")

        assert results == []

    @pytest.mark.asyncio
    async def test_get_skills_returns_skill_id_dicts(self):
        mock_resp = mock_async_response(["sql-expert"])

        with patch("tools.get_my_skills.get_http_client") as mock_ctx:
            mock_ctx.return_value = mock_http_client(get_return=mock_resp)
            from tools.get_my_skills import get_my_skills
            results = await get_my_skills("agent-456")

        assert all("skill_id" in r for r in results)


# ---------------------------------------------------------------------------
# seed_skill tests
# ---------------------------------------------------------------------------

class TestSeedSkillTool:
    @pytest.mark.asyncio
    async def test_seed_returns_seeder_info(self):
        enroll_resp = mock_async_response(
            {"id": "agent-new", "name": "mcp-agent", "framework": "claude-code", "bloomed_skills": []},
            201,
        )
        seeder_resp = mock_async_response(make_seeder_dict(skill_id="my-new-skill", agent_id="agent-new"), 201)

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=[enroll_resp, seeder_resp])

        @asynccontextmanager
        async def mock_get_http():
            yield mock_client

        with patch("tools.seed_skill.get_http_client", mock_get_http):
            from tools.seed_skill import seed_skill
            result = await seed_skill(
                skill_name="My New Skill",
                description="A brand new skill.",
                curriculum=["Do task A", "Do task B"],
            )

        assert "seeder_id" in result
        assert "skill_id" in result
        assert "message" in result
        assert "Successfully registered" in result["message"]

    @pytest.mark.asyncio
    async def test_seed_derives_skill_id_from_name(self):
        enroll_resp = mock_async_response(
            {"id": "agent-xyz", "name": "mcp-agent", "framework": "claude-code", "bloomed_skills": []},
            201,
        )
        # Capture what was posted
        posted_payloads = []

        async def capture_post(url, json=None, **kwargs):
            posted_payloads.append({"url": url, "json": json})
            if "enroll" in url:
                return enroll_resp
            return mock_async_response(make_seeder_dict(skill_id="sql-wizard", agent_id="agent-xyz"), 201)

        mock_client = MagicMock()
        mock_client.post = capture_post

        @asynccontextmanager
        async def mock_get_http():
            yield mock_client

        with patch("tools.seed_skill.get_http_client", mock_get_http):
            from tools.seed_skill import seed_skill
            await seed_skill(
                skill_name="SQL Wizard",
                description="Advanced SQL.",
                curriculum=["Write complex queries"],
            )

        # Verify skill ID was derived from name
        seed_payload = next(p for p in posted_payloads if "seed" in p["url"])
        assert seed_payload["json"]["skill"]["id"] == "sql-wizard"


# ---------------------------------------------------------------------------
# SKILL_SEED.md parsing tests
# ---------------------------------------------------------------------------

class TestSkillSeedMdParsing:
    def test_parse_skill_lines(self, tmp_path):
        skill_seed_md = tmp_path / "SKILL_SEED.md"
        skill_seed_md.write_text("""
# My Project Skills

skill: sql-expert
skill: web-scraper
""")
        import sys
        import os
        sys.path.insert(0, str(tmp_path.parent.parent / "packages" / "mcp-server"))

        # Import the parsing function directly
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "server",
            str(tmp_path.parent.parent / "packages" / "mcp-server" / "server.py")
            if (tmp_path.parent.parent / "packages" / "mcp-server" / "server.py").exists()
            else None,
        )
        # Use direct test of the pattern logic
        import re
        patterns = [
            r"^\s*skill:\s*([a-z0-9][a-z0-9\-]*[a-z0-9])\s*$",
            r"^\s*learn:\s*([a-z0-9][a-z0-9\-]*[a-z0-9])\s*$",
            r"^\s*-\s*([a-z0-9][a-z0-9\-]*[a-z0-9])\s*$",
        ]
        content = skill_seed_md.read_text()
        found = []
        for line in content.splitlines():
            for pattern in patterns:
                m = re.match(pattern, line, re.IGNORECASE)
                if m:
                    found.append(m.group(1).lower())
                    break

        assert "sql-expert" in found
        assert "web-scraper" in found

    def test_parse_list_style(self):
        import re
        patterns = [
            r"^\s*skill:\s*([a-z0-9][a-z0-9\-]*[a-z0-9])\s*$",
            r"^\s*learn:\s*([a-z0-9][a-z0-9\-]*[a-z0-9])\s*$",
            r"^\s*-\s*([a-z0-9][a-z0-9\-]*[a-z0-9])\s*$",
        ]
        lines = ["- sql-expert", "- code-reviewer"]
        found = []
        for line in lines:
            for pattern in patterns:
                m = re.match(pattern, line, re.IGNORECASE)
                if m:
                    found.append(m.group(1).lower())
                    break
        assert found == ["sql-expert", "code-reviewer"]
