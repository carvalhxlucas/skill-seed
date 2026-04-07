"""Tests for the SkillSeed Python SDK using mocked HTTP responses."""

from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock, patch

import httpx

from skillseed.client import SkillSeed
from skillseed.agent import EnrolledAgent
from skillseed.registry import RegistryClient
from skillseed_core.models import AgentProfile, LearningSession, Skill, SeederProfile
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def make_agent_data(agent_id: str = "agent-123", name: str = "TestBot", framework: str = "langchain") -> dict:
    return {
        "id": agent_id,
        "name": name,
        "framework": framework,
        "bloomed_skills": [],
    }


def make_session_data(
    session_id: str = "session-456",
    agent_id: str = "agent-123",
    skill_id: str = "sql-expert",
    status: str = "bloomed",
) -> dict:
    return {
        "id": session_id,
        "agent_id": agent_id,
        "skill_id": skill_id,
        "status": status,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "eval_score": 0.85,
        "learned_state": {"system_prompt_delta": "You are an SQL expert."},
    }


def make_skill_data(skill_id: str = "sql-expert") -> dict:
    return {
        "id": skill_id,
        "name": "SQL Expert",
        "description": "Teaches SQL.",
        "version": "1.0.0",
        "category": "data",
        "curriculum": ["Write a SELECT query"],
        "eval_tasks": ["Find duplicate emails"],
    }


def make_seeder_data(skill_id: str = "sql-expert", agent_id: str = "agent-123") -> dict:
    return {
        "id": "seeder-789",
        "skill_id": skill_id,
        "agent_id": agent_id,
        "reputation_score": 0.0,
        "total_learners": 0,
        "is_root": False,
    }


def mock_response(data: dict | list, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# SkillSeed client tests
# ---------------------------------------------------------------------------

class TestSkillSeedClient:
    def test_init_sets_api_key(self):
        with patch("httpx.Client"):
            ss = SkillSeed(api_key="sk-test", base_url="http://localhost:8000")
            assert ss.api_key == "sk-test"

    def test_enroll_returns_enrolled_agent(self):
        agent_data = make_agent_data()
        mock_resp = mock_response(agent_data, 201)

        with patch("httpx.Client") as MockClient:
            mock_http = MagicMock()
            mock_http.post.return_value = mock_resp
            MockClient.return_value = mock_http

            ss = SkillSeed(api_key="sk-test")
            agent = ss.enroll(name="TestBot", framework="langchain")

            assert isinstance(agent, EnrolledAgent)
            assert agent.id == "agent-123"
            assert agent.name == "TestBot"
            assert agent.framework == "langchain"

    def test_enroll_calls_correct_endpoint(self):
        agent_data = make_agent_data()
        mock_resp = mock_response(agent_data, 201)

        with patch("httpx.Client") as MockClient:
            mock_http = MagicMock()
            mock_http.post.return_value = mock_resp
            MockClient.return_value = mock_http

            ss = SkillSeed(api_key="sk-test")
            ss.enroll(name="TestBot", framework="langchain")

            mock_http.post.assert_called_once_with(
                "/v1/agents/enroll",
                json={"name": "TestBot", "framework": "langchain"},
            )

    def test_seed_returns_seeder_profile(self):
        seeder_data = make_seeder_data()
        mock_resp = mock_response(seeder_data, 201)

        with patch("httpx.Client") as MockClient:
            mock_http = MagicMock()
            mock_http.post.return_value = mock_resp
            MockClient.return_value = mock_http

            ss = SkillSeed(api_key="sk-test")
            skill = Skill(**make_skill_data())
            seeder = ss.seed(agent_id="agent-123", skill=skill)

            assert isinstance(seeder, SeederProfile)
            assert seeder.skill_id == "sql-expert"
            assert seeder.is_root is False

    def test_context_manager(self):
        with patch("httpx.Client") as MockClient:
            mock_http = MagicMock()
            MockClient.return_value = mock_http

            with SkillSeed(api_key="sk-test") as ss:
                assert ss.api_key == "sk-test"

            mock_http.close.assert_called_once()


# ---------------------------------------------------------------------------
# EnrolledAgent tests
# ---------------------------------------------------------------------------

class TestEnrolledAgent:
    def _make_agent(self, mock_http: MagicMock) -> EnrolledAgent:
        profile = AgentProfile(**make_agent_data())
        return EnrolledAgent(profile=profile, client=mock_http)

    def test_learn_returns_session_immediately_if_bloomed(self):
        mock_http = MagicMock()
        session_data = make_session_data(status="bloomed")
        mock_resp = mock_response(session_data, 201)
        profile_resp = mock_response(make_agent_data())

        mock_http.post.return_value = mock_resp
        mock_http.get.return_value = profile_resp

        agent = self._make_agent(mock_http)
        session = agent.learn("sql-expert")

        assert isinstance(session, LearningSession)
        assert session.status == "bloomed"
        assert session.skill_id == "sql-expert"

    def test_learn_polls_until_terminal(self):
        mock_http = MagicMock()

        # First POST returns "learning", then GET returns "bloomed"
        learning_data = make_session_data(status="learning")
        bloomed_data = make_session_data(status="bloomed")
        profile_data = make_agent_data()

        post_resp = mock_response(learning_data, 201)
        get_session_resp = mock_response(bloomed_data)
        get_profile_resp = mock_response(profile_data)

        mock_http.post.return_value = post_resp
        mock_http.get.side_effect = [get_session_resp, get_profile_resp]

        agent = self._make_agent(mock_http)
        session = agent.learn("sql-expert", poll_interval=0)

        assert session.status == "bloomed"

    def test_learn_failed_status_returns_session(self):
        mock_http = MagicMock()
        session_data = make_session_data(status="failed")
        mock_resp = mock_response(session_data, 201)
        profile_resp = mock_response(make_agent_data())

        mock_http.post.return_value = mock_resp
        mock_http.get.return_value = profile_resp

        agent = self._make_agent(mock_http)
        session = agent.learn("sql-expert")
        assert session.status == "failed"

    def test_my_skills_returns_list(self):
        mock_http = MagicMock()
        mock_http.get.return_value = mock_response(["sql-expert", "web-scraper"])

        agent = self._make_agent(mock_http)
        skills = agent.my_skills()

        assert "sql-expert" in skills
        assert "web-scraper" in skills

    def test_my_skills_updates_local_profile(self):
        mock_http = MagicMock()
        mock_http.get.return_value = mock_response(["sql-expert"])

        agent = self._make_agent(mock_http)
        agent.my_skills()
        assert "sql-expert" in agent.profile.bloomed_skills

    def test_seed_via_agent(self):
        mock_http = MagicMock()
        seeder_data = make_seeder_data()
        mock_http.post.return_value = mock_response(seeder_data, 201)

        agent = self._make_agent(mock_http)
        skill = Skill(**make_skill_data())
        seeder = agent.seed(skill)

        assert isinstance(seeder, SeederProfile)
        assert seeder.agent_id == "agent-123"

    def test_repr(self):
        mock_http = MagicMock()
        agent = self._make_agent(mock_http)
        r = repr(agent)
        assert "TestBot" in r
        assert "langchain" in r


# ---------------------------------------------------------------------------
# RegistryClient tests
# ---------------------------------------------------------------------------

class TestRegistryClient:
    def _make_registry(self, mock_http: MagicMock) -> RegistryClient:
        return RegistryClient(http=mock_http)

    def test_list_returns_skills(self):
        mock_http = MagicMock()
        mock_http.get.return_value = mock_response([make_skill_data()])

        registry = self._make_registry(mock_http)
        skills = registry.list()

        assert len(skills) == 1
        assert isinstance(skills[0], Skill)
        assert skills[0].id == "sql-expert"

    def test_search_with_query(self):
        mock_http = MagicMock()
        mock_http.get.return_value = mock_response([make_skill_data()])

        registry = self._make_registry(mock_http)
        skills = registry.search(query="sql")

        mock_http.get.assert_called_once_with(
            "/v1/skills/registry",
            params={"search": "sql"},
        )
        assert len(skills) == 1

    def test_search_with_category(self):
        mock_http = MagicMock()
        mock_http.get.return_value = mock_response([make_skill_data()])

        registry = self._make_registry(mock_http)
        registry.search(category="data")

        mock_http.get.assert_called_once_with(
            "/v1/skills/registry",
            params={"category": "data"},
        )

    def test_search_empty_params_excluded(self):
        mock_http = MagicMock()
        mock_http.get.return_value = mock_response([])

        registry = self._make_registry(mock_http)
        registry.search()

        mock_http.get.assert_called_once_with(
            "/v1/skills/registry",
            params={},
        )

    def test_get_skill_found(self):
        mock_http = MagicMock()
        mock_http.get.return_value = mock_response([make_skill_data("sql-expert")])

        registry = self._make_registry(mock_http)
        skill = registry.get("sql-expert")

        assert skill is not None
        assert skill.id == "sql-expert"

    def test_get_skill_not_found(self):
        mock_http = MagicMock()
        mock_http.get.return_value = mock_response([])

        registry = self._make_registry(mock_http)
        skill = registry.get("nonexistent")
        assert skill is None
