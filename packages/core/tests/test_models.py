"""Tests for core SkillSeed models, registry, protocol, and evaluators."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from skillseed_core.models import AgentProfile, LearningSession, Skill, SeederProfile
from skillseed_core.registry import SkillRegistry
from skillseed_core.eval import SimpleEvaluator, KeywordEvaluator
from skillseed_core.protocol import PromptDistillationProtocol, TraceDemonstrationProtocol, CritiqueLoopProtocol


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sql_skill() -> Skill:
    return Skill(
        id="sql-expert",
        name="SQL Expert",
        description="Teaches efficient SQL query writing.",
        version="1.0.0",
        category="data",
        curriculum=[
            "Write a query to find the top 5 customers by total order value",
            "Write a query using a LEFT JOIN between orders and customers",
        ],
        eval_tasks=[
            "Find all users who placed more than 3 orders in the last 30 days",
        ],
    )


@pytest.fixture
def agent_profile() -> AgentProfile:
    return AgentProfile(
        id="agent-001",
        name="TestBot",
        framework="langchain",
        bloomed_skills=[],
    )


@pytest.fixture
def seeder_profile(sql_skill) -> SeederProfile:
    return SeederProfile(
        id="seeder-001",
        skill_id=sql_skill.id,
        agent_id="root-agent",
        reputation_score=4.8,
        total_learners=120,
        is_root=True,
    )


@pytest.fixture
def learning_session() -> LearningSession:
    return LearningSession(
        id="session-001",
        agent_id="agent-001",
        skill_id="sql-expert",
        status="pending",
        started_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Skill tests
# ---------------------------------------------------------------------------

class TestSkill:
    def test_skill_creation(self, sql_skill):
        assert sql_skill.id == "sql-expert"
        assert sql_skill.name == "SQL Expert"
        assert sql_skill.version == "1.0.0"
        assert sql_skill.category == "data"

    def test_skill_curriculum_is_list(self, sql_skill):
        assert isinstance(sql_skill.curriculum, list)
        assert len(sql_skill.curriculum) == 2

    def test_skill_eval_tasks_is_list(self, sql_skill):
        assert isinstance(sql_skill.eval_tasks, list)
        assert len(sql_skill.eval_tasks) == 1

    def test_skill_requires_all_fields(self):
        with pytest.raises(Exception):
            Skill(id="x", name="X")  # missing required fields

    def test_skill_description_stored(self, sql_skill):
        assert "SQL" in sql_skill.description

    def test_skill_serialization(self, sql_skill):
        data = sql_skill.model_dump()
        assert data["id"] == "sql-expert"
        assert "curriculum" in data
        assert "eval_tasks" in data

    def test_skill_from_dict(self):
        data = {
            "id": "web-scraper",
            "name": "Web Scraper",
            "description": "Scraping the web.",
            "version": "0.2.0",
            "category": "automation",
            "curriculum": ["Scrape a table from HTML"],
            "eval_tasks": ["Extract all links from a page"],
        }
        skill = Skill(**data)
        assert skill.id == "web-scraper"
        assert skill.category == "automation"


# ---------------------------------------------------------------------------
# AgentProfile tests
# ---------------------------------------------------------------------------

class TestAgentProfile:
    def test_agent_creation(self, agent_profile):
        assert agent_profile.id == "agent-001"
        assert agent_profile.name == "TestBot"
        assert agent_profile.framework == "langchain"

    def test_agent_empty_bloomed_skills_by_default(self):
        agent = AgentProfile(id="a", name="Bot", framework="custom")
        assert agent.bloomed_skills == []

    def test_agent_bloomed_skills_list(self, agent_profile):
        agent_profile.bloomed_skills.append("sql-expert")
        assert "sql-expert" in agent_profile.bloomed_skills

    def test_agent_multiple_skills(self, agent_profile):
        agent_profile.bloomed_skills = ["sql-expert", "web-scraper"]
        assert len(agent_profile.bloomed_skills) == 2

    def test_agent_serialization(self, agent_profile):
        data = agent_profile.model_dump()
        assert "bloomed_skills" in data
        assert isinstance(data["bloomed_skills"], list)


# ---------------------------------------------------------------------------
# LearningSession tests
# ---------------------------------------------------------------------------

class TestLearningSession:
    def test_session_initial_status(self, learning_session):
        assert learning_session.status == "pending"

    def test_session_status_transitions(self, learning_session):
        for status in ["pending", "learning", "evaluating", "bloomed", "failed"]:
            learning_session.status = status
            assert learning_session.status == status

    def test_session_invalid_status(self):
        with pytest.raises(Exception):
            LearningSession(
                id="s1",
                agent_id="a1",
                skill_id="sql-expert",
                status="invalid_status",
                started_at=datetime.now(timezone.utc),
            )

    def test_session_completed_at_defaults_none(self, learning_session):
        assert learning_session.completed_at is None

    def test_session_eval_score_defaults_none(self, learning_session):
        assert learning_session.eval_score is None

    def test_session_learned_state_defaults_empty(self, learning_session):
        assert learning_session.learned_state == {}

    def test_session_can_set_completed_at(self, learning_session):
        now = datetime.now(timezone.utc)
        learning_session.completed_at = now
        assert learning_session.completed_at == now

    def test_session_can_set_eval_score(self, learning_session):
        learning_session.eval_score = 0.85
        assert learning_session.eval_score == 0.85

    def test_session_learned_state_mutable(self, learning_session):
        learning_session.learned_state = {"system_prompt_delta": "You are an SQL expert."}
        assert "system_prompt_delta" in learning_session.learned_state


# ---------------------------------------------------------------------------
# SeederProfile tests
# ---------------------------------------------------------------------------

class TestSeederProfile:
    def test_seeder_root_true(self, seeder_profile):
        assert seeder_profile.is_root is True

    def test_seeder_root_false(self):
        seeder = SeederProfile(
            id="s2",
            skill_id="web-scraper",
            agent_id="community-agent",
            reputation_score=3.2,
            total_learners=10,
            is_root=False,
        )
        assert seeder.is_root is False

    def test_seeder_reputation_score(self, seeder_profile):
        assert seeder_profile.reputation_score == 4.8

    def test_seeder_total_learners(self, seeder_profile):
        assert seeder_profile.total_learners == 120

    def test_seeder_defaults(self):
        seeder = SeederProfile(
            id="s3",
            skill_id="code-reviewer",
            agent_id="bot-x",
        )
        assert seeder.reputation_score == 0.0
        assert seeder.total_learners == 0
        assert seeder.is_root is False

    def test_seeder_serialization(self, seeder_profile):
        data = seeder_profile.model_dump()
        assert data["is_root"] is True
        assert data["skill_id"] == "sql-expert"


# ---------------------------------------------------------------------------
# SkillRegistry tests
# ---------------------------------------------------------------------------

class TestSkillRegistry:
    def test_register_and_get(self, sql_skill):
        registry = SkillRegistry()
        registry.register(sql_skill)
        result = registry.get("sql-expert")
        assert result is not None
        assert result.id == "sql-expert"

    def test_get_nonexistent_returns_none(self):
        registry = SkillRegistry()
        assert registry.get("nonexistent") is None

    def test_list_all_empty(self):
        registry = SkillRegistry()
        assert registry.list_all() == []

    def test_list_all_returns_all_skills(self, sql_skill):
        registry = SkillRegistry()
        skill2 = Skill(
            id="web-scraper",
            name="Web Scraper",
            description="Web scraping skill",
            version="1.0.0",
            category="automation",
            curriculum=["Scrape HTML"],
            eval_tasks=["Extract links"],
        )
        registry.register(sql_skill)
        registry.register(skill2)
        all_skills = registry.list_all()
        assert len(all_skills) == 2

    def test_search_by_query(self, sql_skill):
        registry = SkillRegistry()
        registry.register(sql_skill)
        results = registry.search(query="SQL")
        assert len(results) == 1
        assert results[0].id == "sql-expert"

    def test_search_by_category(self, sql_skill):
        registry = SkillRegistry()
        registry.register(sql_skill)
        skill2 = Skill(
            id="web-scraper",
            name="Web Scraper",
            description="Web scraping",
            version="1.0.0",
            category="automation",
            curriculum=[],
            eval_tasks=[],
        )
        registry.register(skill2)
        results = registry.search(category="data")
        assert len(results) == 1
        assert results[0].id == "sql-expert"

    def test_search_no_match(self, sql_skill):
        registry = SkillRegistry()
        registry.register(sql_skill)
        results = registry.search(query="nonexistent_xyz")
        assert results == []

    def test_search_by_query_and_category(self, sql_skill):
        registry = SkillRegistry()
        registry.register(sql_skill)
        results = registry.search(query="sql", category="data")
        assert len(results) == 1

    def test_search_empty_returns_all(self, sql_skill):
        registry = SkillRegistry()
        registry.register(sql_skill)
        results = registry.search()
        assert len(results) == 1

    def test_register_overwrites_existing(self, sql_skill):
        registry = SkillRegistry()
        registry.register(sql_skill)
        updated = Skill(
            id="sql-expert",
            name="SQL Expert v2",
            description="Updated.",
            version="2.0.0",
            category="data",
            curriculum=[],
            eval_tasks=[],
        )
        registry.register(updated)
        result = registry.get("sql-expert")
        assert result.name == "SQL Expert v2"

    def test_len(self, sql_skill):
        registry = SkillRegistry()
        assert len(registry) == 0
        registry.register(sql_skill)
        assert len(registry) == 1

    def test_contains(self, sql_skill):
        registry = SkillRegistry()
        registry.register(sql_skill)
        assert "sql-expert" in registry
        assert "missing-skill" not in registry

    def test_unregister(self, sql_skill):
        registry = SkillRegistry()
        registry.register(sql_skill)
        removed = registry.unregister("sql-expert")
        assert removed is True
        assert registry.get("sql-expert") is None

    def test_unregister_nonexistent(self):
        registry = SkillRegistry()
        removed = registry.unregister("nope")
        assert removed is False


# ---------------------------------------------------------------------------
# Evaluator tests
# ---------------------------------------------------------------------------

class TestEvaluators:
    @pytest.mark.asyncio
    async def test_simple_evaluator_returns_08(self, learning_session, sql_skill):
        evaluator = SimpleEvaluator()
        score = await evaluator.evaluate(learning_session, sql_skill)
        assert score == 0.8

    @pytest.mark.asyncio
    async def test_keyword_evaluator_with_matching_prompt(self, sql_skill):
        session = LearningSession(
            id="s",
            agent_id="a",
            skill_id="sql-expert",
            status="evaluating",
            started_at=datetime.now(timezone.utc),
            learned_state={"system_prompt_delta": "You are an expert in SQL."},
        )
        evaluator = KeywordEvaluator()
        score = await evaluator.evaluate(session, sql_skill)
        assert score > 0.0

    @pytest.mark.asyncio
    async def test_keyword_evaluator_empty_prompt(self, sql_skill):
        session = LearningSession(
            id="s",
            agent_id="a",
            skill_id="sql-expert",
            status="evaluating",
            started_at=datetime.now(timezone.utc),
            learned_state={},
        )
        evaluator = KeywordEvaluator()
        score = await evaluator.evaluate(session, sql_skill)
        assert score == 0.0


# ---------------------------------------------------------------------------
# Protocol tests
# ---------------------------------------------------------------------------

class TestProtocol:
    @pytest.mark.asyncio
    async def test_prompt_distillation_produces_bloomed_session(self, sql_skill, seeder_profile, agent_profile):
        protocol = PromptDistillationProtocol(threshold=0.7)
        session = await protocol.transfer(sql_skill, seeder_profile, agent_profile)
        assert session.status == "bloomed"
        assert session.eval_score is not None
        assert session.eval_score >= 0.7
        assert "system_prompt_delta" in session.learned_state

    @pytest.mark.asyncio
    async def test_prompt_distillation_updates_grower_skills(self, sql_skill, seeder_profile, agent_profile):
        protocol = PromptDistillationProtocol(threshold=0.7)
        await protocol.transfer(sql_skill, seeder_profile, agent_profile)
        assert "sql-expert" in agent_profile.bloomed_skills

    @pytest.mark.asyncio
    async def test_prompt_distillation_session_has_completed_at(self, sql_skill, seeder_profile, agent_profile):
        protocol = PromptDistillationProtocol(threshold=0.7)
        session = await protocol.transfer(sql_skill, seeder_profile, agent_profile)
        assert session.completed_at is not None

    @pytest.mark.asyncio
    async def test_trace_protocol_raises_not_implemented(self, sql_skill, seeder_profile, agent_profile):
        protocol = TraceDemonstrationProtocol()
        with pytest.raises(NotImplementedError):
            await protocol.transfer(sql_skill, seeder_profile, agent_profile)

    @pytest.mark.asyncio
    async def test_critique_loop_protocol_raises_not_implemented(self, sql_skill, seeder_profile, agent_profile):
        protocol = CritiqueLoopProtocol()
        with pytest.raises(NotImplementedError):
            await protocol.transfer(sql_skill, seeder_profile, agent_profile)
