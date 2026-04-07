"""Integration tests for the SkillSeed API routers."""

from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

import sys
import os

# Ensure the api package root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import app


@pytest.fixture
async def client():
    """Async HTTP client pointed at the test app."""
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=True), base_url="http://test", headers={"lifespan": "on"}) as ac:
        # Manually trigger lifespan startup so app.state is populated
        from services.learning_service import LearningService
        from services.eval_service import EvalService
        app.state.learning_service = LearningService()
        app.state.eval_service = EvalService()
        yield ac


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------

class TestHealth:
    @pytest.mark.asyncio
    async def test_root(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "skillseed-api"

    @pytest.mark.asyncio
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Agent endpoints
# ---------------------------------------------------------------------------

class TestAgentsRouter:
    @pytest.mark.asyncio
    async def test_enroll_agent(self, client):
        resp = await client.post(
            "/v1/agents/enroll",
            json={"name": "TestBot", "framework": "langchain"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "TestBot"
        assert data["framework"] == "langchain"
        assert "id" in data
        assert data["bloomed_skills"] == []

    @pytest.mark.asyncio
    async def test_enroll_agent_empty_name(self, client):
        resp = await client.post(
            "/v1/agents/enroll",
            json={"name": "  ", "framework": "langchain"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_enroll_agent_empty_framework(self, client):
        resp = await client.post(
            "/v1/agents/enroll",
            json={"name": "Bot", "framework": ""},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_enroll_agent_missing_fields(self, client):
        resp = await client.post("/v1/agents/enroll", json={"name": "Bot"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_get_agent_skills_empty(self, client):
        enroll = await client.post(
            "/v1/agents/enroll",
            json={"name": "SkilllessBot", "framework": "custom"},
        )
        agent_id = enroll.json()["id"]
        resp = await client.get(f"/v1/agents/{agent_id}/skills")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_get_agent_skills_not_found(self, client):
        resp = await client.get("/v1/agents/nonexistent-id/skills")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_agent_profile(self, client):
        enroll = await client.post(
            "/v1/agents/enroll",
            json={"name": "ProfileBot", "framework": "crewai"},
        )
        agent_id = enroll.json()["id"]
        resp = await client.get(f"/v1/agents/{agent_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == agent_id
        assert data["framework"] == "crewai"

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, client):
        resp = await client.get("/v1/agents/does-not-exist")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Skills registry endpoints
# ---------------------------------------------------------------------------

class TestSkillsRouter:
    @pytest.mark.asyncio
    async def test_get_registry_returns_built_ins(self, client):
        resp = await client.get("/v1/skills/registry")
        assert resp.status_code == 200
        skills = resp.json()
        assert len(skills) >= 3
        ids = [s["id"] for s in skills]
        assert "sql-expert" in ids
        assert "web-scraper" in ids
        assert "code-reviewer" in ids

    @pytest.mark.asyncio
    async def test_get_registry_filter_by_category(self, client):
        resp = await client.get("/v1/skills/registry?category=data")
        assert resp.status_code == 200
        skills = resp.json()
        assert all(s["category"] == "data" for s in skills)

    @pytest.mark.asyncio
    async def test_get_registry_search(self, client):
        resp = await client.get("/v1/skills/registry?search=SQL")
        assert resp.status_code == 200
        skills = resp.json()
        assert len(skills) >= 1
        assert any(s["id"] == "sql-expert" for s in skills)

    @pytest.mark.asyncio
    async def test_get_registry_search_no_match(self, client):
        resp = await client.get("/v1/skills/registry?search=xyznonexistent123")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# Learning session endpoints
# ---------------------------------------------------------------------------

class TestLearningRouter:
    @pytest.mark.asyncio
    async def test_start_learning_success(self, client):
        enroll = await client.post(
            "/v1/agents/enroll",
            json={"name": "Learner", "framework": "langchain"},
        )
        agent_id = enroll.json()["id"]

        resp = await client.post(
            "/v1/skills/learn",
            json={"agent_id": agent_id, "skill_id": "sql-expert"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["agent_id"] == agent_id
        assert data["skill_id"] == "sql-expert"
        assert data["status"] in ("bloomed", "failed")
        assert "id" in data

    @pytest.mark.asyncio
    async def test_start_learning_unknown_agent(self, client):
        resp = await client.post(
            "/v1/skills/learn",
            json={"agent_id": "ghost-agent", "skill_id": "sql-expert"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_start_learning_unknown_skill(self, client):
        enroll = await client.post(
            "/v1/agents/enroll",
            json={"name": "Bot2", "framework": "custom"},
        )
        agent_id = enroll.json()["id"]
        resp = await client.post(
            "/v1/skills/learn",
            json={"agent_id": agent_id, "skill_id": "nonexistent-skill"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_session(self, client):
        enroll = await client.post(
            "/v1/agents/enroll",
            json={"name": "SessionBot", "framework": "langgraph"},
        )
        agent_id = enroll.json()["id"]

        learn = await client.post(
            "/v1/skills/learn",
            json={"agent_id": agent_id, "skill_id": "web-scraper"},
        )
        session_id = learn.json()["id"]

        resp = await client.get(f"/v1/skills/learn/{session_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == session_id

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, client):
        resp = await client.get("/v1/skills/learn/nonexistent-session")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_learning_updates_agent_skills(self, client):
        enroll = await client.post(
            "/v1/agents/enroll",
            json={"name": "SkillTracker", "framework": "autogen"},
        )
        agent_id = enroll.json()["id"]

        learn = await client.post(
            "/v1/skills/learn",
            json={"agent_id": agent_id, "skill_id": "sql-expert"},
        )
        assert learn.json()["status"] == "bloomed"

        skills = await client.get(f"/v1/agents/{agent_id}/skills")
        assert "sql-expert" in skills.json()


# ---------------------------------------------------------------------------
# Seed endpoint
# ---------------------------------------------------------------------------

class TestSeedRouter:
    @pytest.mark.asyncio
    async def test_seed_skill(self, client):
        enroll = await client.post(
            "/v1/agents/enroll",
            json={"name": "Seeder", "framework": "custom"},
        )
        agent_id = enroll.json()["id"]

        skill_payload = {
            "id": "my-custom-skill",
            "name": "My Custom Skill",
            "description": "A custom skill contributed by community.",
            "version": "0.1.0",
            "category": "custom",
            "curriculum": ["Do task A", "Do task B"],
            "eval_tasks": ["Validate task A"],
        }

        resp = await client.post(
            "/v1/skills/seed",
            json={"agent_id": agent_id, "skill": skill_payload},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["skill_id"] == "my-custom-skill"
        assert data["agent_id"] == agent_id
        assert data["is_root"] is False

    @pytest.mark.asyncio
    async def test_seed_skill_unknown_agent(self, client):
        skill_payload = {
            "id": "orphan-skill",
            "name": "Orphan",
            "description": "No agent.",
            "version": "1.0.0",
            "category": "misc",
            "curriculum": [],
            "eval_tasks": [],
        }
        resp = await client.post(
            "/v1/skills/seed",
            json={"agent_id": "ghost-agent", "skill": skill_payload},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_seed_skill_appears_in_registry(self, client):
        enroll = await client.post(
            "/v1/agents/enroll",
            json={"name": "Contributor", "framework": "langchain"},
        )
        agent_id = enroll.json()["id"]

        skill_payload = {
            "id": "community-skill-xyz",
            "name": "Community Skill XYZ",
            "description": "A community skill.",
            "version": "0.1.0",
            "category": "community",
            "curriculum": ["Learn X"],
            "eval_tasks": ["Test X"],
        }

        await client.post(
            "/v1/skills/seed",
            json={"agent_id": agent_id, "skill": skill_payload},
        )

        registry = await client.get("/v1/skills/registry?search=Community+Skill+XYZ")
        ids = [s["id"] for s in registry.json()]
        assert "community-skill-xyz" in ids
