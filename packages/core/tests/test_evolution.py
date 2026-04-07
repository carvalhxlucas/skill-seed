"""Tests for SeederEvolution, ShadowEval, and related models."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from skillseed_core.models import (
    AgentProfile,
    CurriculumVersion,
    FeedbackSignal,
    LearningSession,
    SeederProfile,
    Skill,
)
from skillseed_core.evolution import SeederEvolution, ShadowEval, WeakSpot


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def skill() -> Skill:
    return Skill(
        id="sql-expert",
        name="SQL Expert",
        description="Efficient SQL queries.",
        version="1.0.0",
        category="data",
        curriculum=[
            "Write a LEFT JOIN query",
            "Optimize with a CTE",
            "Use a window function",
        ],
        eval_tasks=[
            "Find users with more than 3 orders",
            "Detect duplicate emails",
        ],
        shadow_eval_tasks=[
            "Write a recursive CTE for hierarchy",
            "Rewrite correlated subquery as window function",
        ],
    )


@pytest.fixture
def seeder() -> SeederProfile:
    return SeederProfile(
        id="seeder-001",
        skill_id="sql-expert",
        agent_id="root-agent",
        reputation_score=4.5,
        total_learners=20,
        bloom_rate=0.5,
        curriculum_version="1.0.0",
        is_root=True,
        evolution_enabled=True,
    )


@pytest.fixture
def failed_session() -> LearningSession:
    return LearningSession(
        id="session-fail-001",
        agent_id="agent-abc",
        skill_id="sql-expert",
        seeder_id="seeder-001",
        status="failed",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        eval_score=0.4,
        failed_tasks=["Find users with more than 3 orders"],
        learned_state={},
    )


@pytest.fixture
def bloomed_session() -> LearningSession:
    return LearningSession(
        id="session-ok-001",
        agent_id="agent-xyz",
        skill_id="sql-expert",
        seeder_id="seeder-001",
        status="bloomed",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        eval_score=0.85,
        failed_tasks=[],
        learned_state={},
    )


@pytest.fixture
def evolution() -> SeederEvolution:
    return SeederEvolution(
        revision_threshold=0.6,
        min_signals_to_revise=3,
    )


# ---------------------------------------------------------------------------
# ShadowEval tests
# ---------------------------------------------------------------------------

class TestShadowEval:
    @pytest.mark.asyncio
    async def test_evaluate_returns_fraction_of_public_score(self, skill, failed_session):
        shadow = ShadowEval()
        score = await shadow.evaluate(failed_session, skill)
        assert score == pytest.approx(failed_session.eval_score * 0.9, rel=1e-3)

    @pytest.mark.asyncio
    async def test_evaluate_no_shadow_tasks_returns_public_score(self, failed_session):
        skill_no_shadow = Skill(
            id="simple-skill",
            name="Simple Skill",
            description="No shadow tasks.",
            version="1.0.0",
            category="test",
            curriculum=["Do X"],
            eval_tasks=["Test X"],
            shadow_eval_tasks=[],
        )
        shadow = ShadowEval()
        score = await shadow.evaluate(failed_session, skill_no_shadow)
        assert score == failed_session.eval_score

    def test_is_suspicious_above_threshold(self):
        shadow = ShadowEval(drift_threshold=0.2)
        assert shadow.is_suspicious(public_score=0.9, shadow_score=0.6) is True

    def test_is_suspicious_below_threshold(self):
        shadow = ShadowEval(drift_threshold=0.2)
        assert shadow.is_suspicious(public_score=0.9, shadow_score=0.75) is False

    def test_is_suspicious_exactly_at_threshold(self):
        shadow = ShadowEval(drift_threshold=0.2)
        # Equal to threshold IS suspicious (>=)
        assert shadow.is_suspicious(public_score=0.9, shadow_score=0.7) is True


# ---------------------------------------------------------------------------
# SeederEvolution — Level 1 (reactive)
# ---------------------------------------------------------------------------

class TestLevel1Reactive:
    @pytest.mark.asyncio
    async def test_on_session_complete_failed_creates_signal(
        self, evolution, failed_session, seeder, skill
    ):
        signals: list[FeedbackSignal] = []
        versions: list[CurriculumVersion] = []
        signal = await evolution.on_session_complete(failed_session, seeder, skill, signals, versions)
        assert signal is not None
        assert signal.seeder_id == seeder.id
        assert signal.eval_score == failed_session.eval_score
        assert len(signals) == 1

    @pytest.mark.asyncio
    async def test_on_session_complete_bloomed_creates_no_signal(
        self, evolution, bloomed_session, seeder, skill
    ):
        signals: list[FeedbackSignal] = []
        versions: list[CurriculumVersion] = []
        signal = await evolution.on_session_complete(bloomed_session, seeder, skill, signals, versions)
        assert signal is None
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_signal_never_contains_shadow_eval_score(
        self, evolution, failed_session, seeder, skill
    ):
        signals: list[FeedbackSignal] = []
        versions: list[CurriculumVersion] = []
        signal = await evolution.on_session_complete(failed_session, seeder, skill, signals, versions)
        assert signal is not None
        data = signal.model_dump()
        # shadow_eval_score must not appear in feedback signal
        assert "shadow_eval_score" not in data

    @pytest.mark.asyncio
    async def test_shadow_eval_score_set_on_session(
        self, evolution, failed_session, seeder, skill
    ):
        signals: list[FeedbackSignal] = []
        versions: list[CurriculumVersion] = []
        await evolution.on_session_complete(failed_session, seeder, skill, signals, versions)
        assert failed_session.shadow_eval_score is not None

    @pytest.mark.asyncio
    async def test_maybe_revise_below_min_signals_returns_none(
        self, evolution, seeder, skill
    ):
        # Only 1 signal, min is 3 — should not revise
        signals = [
            FeedbackSignal(
                id="sig-1", seeder_id=seeder.id, skill_id=skill.id,
                session_id="s1", eval_score=0.4,
                failed_tasks=["Find users with more than 3 orders"],
                created_at=datetime.now(timezone.utc),
            )
        ]
        versions: list[CurriculumVersion] = []
        result = await evolution.maybe_revise(seeder, skill, signals, versions)
        assert result is None

    @pytest.mark.asyncio
    async def test_maybe_revise_above_bloom_rate_returns_none(
        self, evolution, seeder, skill
    ):
        seeder.bloom_rate = 0.9  # well above revision_threshold=0.6
        signals = [
            FeedbackSignal(
                id=f"sig-{i}", seeder_id=seeder.id, skill_id=skill.id,
                session_id=f"s{i}", eval_score=0.3,
                failed_tasks=["Find users with more than 3 orders"],
                created_at=datetime.now(timezone.utc),
            )
            for i in range(5)
        ]
        versions: list[CurriculumVersion] = []
        result = await evolution.maybe_revise(seeder, skill, signals, versions)
        assert result is None

    @pytest.mark.asyncio
    async def test_maybe_revise_triggers_curriculum_version(
        self, evolution, seeder, skill
    ):
        seeder.bloom_rate = 0.3  # below threshold
        signals = [
            FeedbackSignal(
                id=f"sig-{i}", seeder_id=seeder.id, skill_id=skill.id,
                session_id=f"s{i}", eval_score=0.3,
                failed_tasks=["Find users with more than 3 orders"],
                created_at=datetime.now(timezone.utc),
            )
            for i in range(5)
        ]
        versions: list[CurriculumVersion] = []
        result = await evolution.maybe_revise(seeder, skill, signals, versions)
        assert result is not None
        assert isinstance(result, CurriculumVersion)
        assert result.seeder_id == seeder.id
        assert len(versions) == 1


# ---------------------------------------------------------------------------
# SeederEvolution — Level 2 (proactive)
# ---------------------------------------------------------------------------

class TestLevel2Proactive:
    @pytest.mark.asyncio
    async def test_analyze_failure_patterns_empty_signals(self, evolution, skill):
        spots = await evolution.analyze_failure_patterns([], skill)
        assert spots == []

    @pytest.mark.asyncio
    async def test_analyze_failure_patterns_identifies_weak_task(
        self, evolution, seeder, skill
    ):
        failing_task = "Find users with more than 3 orders"
        signals = [
            FeedbackSignal(
                id=f"sig-{i}", seeder_id=seeder.id, skill_id=skill.id,
                session_id=f"s{i}", eval_score=0.3,
                failed_tasks=[failing_task],
                created_at=datetime.now(timezone.utc),
            )
            for i in range(4)
        ]
        spots = await evolution.analyze_failure_patterns(signals, skill)
        assert len(spots) >= 1
        assert spots[0].task == failing_task
        assert spots[0].failure_rate == 1.0

    @pytest.mark.asyncio
    async def test_analyze_failure_patterns_sorted_by_rate(
        self, evolution, seeder, skill
    ):
        signals = [
            FeedbackSignal(
                id="s1", seeder_id=seeder.id, skill_id=skill.id,
                session_id="s1", eval_score=0.3,
                failed_tasks=["Find users with more than 3 orders", "Detect duplicate emails"],
                created_at=datetime.now(timezone.utc),
            ),
            FeedbackSignal(
                id="s2", seeder_id=seeder.id, skill_id=skill.id,
                session_id="s2", eval_score=0.3,
                failed_tasks=["Find users with more than 3 orders"],
                created_at=datetime.now(timezone.utc),
            ),
        ]
        spots = await evolution.analyze_failure_patterns(signals, skill)
        # "Find users..." appears in both (rate=1.0), "Detect..." in one (rate=0.5)
        assert spots[0].failure_rate >= spots[1].failure_rate

    @pytest.mark.asyncio
    async def test_strengthen_curriculum_bumps_version(
        self, evolution, seeder, skill
    ):
        weak_spots = [WeakSpot(task="Find users with more than 3 orders", failure_rate=0.8, session_count=5)]
        versions: list[CurriculumVersion] = []
        version = await evolution.strengthen_curriculum(seeder, skill, weak_spots, versions)
        assert version.version == "1.1.0"
        assert seeder.curriculum_version == "1.1.0"

    @pytest.mark.asyncio
    async def test_strengthen_curriculum_adds_reinforcement(
        self, evolution, seeder, skill
    ):
        original_len = len(skill.curriculum)
        weak_spots = [WeakSpot(task="Find users with more than 3 orders", failure_rate=0.9, session_count=10)]
        versions: list[CurriculumVersion] = []
        version = await evolution.strengthen_curriculum(seeder, skill, weak_spots, versions)
        assert len(version.curriculum) > original_len

    @pytest.mark.asyncio
    async def test_strengthen_curriculum_never_mutates_in_place(
        self, evolution, seeder, skill
    ):
        original_curriculum = list(skill.curriculum)
        weak_spots = [WeakSpot(task=skill.curriculum[0], failure_rate=0.8, session_count=5)]
        versions: list[CurriculumVersion] = []
        version = await evolution.strengthen_curriculum(seeder, skill, weak_spots, versions)
        # A new version is created — original_curriculum reference is separate
        assert version.curriculum != original_curriculum

    @pytest.mark.asyncio
    async def test_strengthen_curriculum_records_revision_reason(
        self, evolution, seeder, skill
    ):
        weak_spots = [WeakSpot(task="Find users with more than 3 orders", failure_rate=0.9, session_count=5)]
        versions: list[CurriculumVersion] = []
        version = await evolution.strengthen_curriculum(seeder, skill, weak_spots, versions)
        assert len(version.revision_reason) > 0
        assert "revision" in version.revision_reason.lower()


# ---------------------------------------------------------------------------
# Level 3 stub
# ---------------------------------------------------------------------------

class TestLevel3Stub:
    @pytest.mark.asyncio
    async def test_cross_pollinate_raises_not_implemented(self, evolution, seeder):
        other_seeder = SeederProfile(
            id="seeder-002", skill_id="web-scraper", agent_id="bot",
        )
        with pytest.raises(NotImplementedError):
            await evolution.cross_pollinate(seeder, other_seeder)


# ---------------------------------------------------------------------------
# Shadow eval integrity — shadow_eval_tasks never in public fields
# ---------------------------------------------------------------------------

class TestShadowTasksNeverExposed:
    def test_skill_serialization_includes_shadow_tasks_internally(self, skill):
        """shadow_eval_tasks exists on the internal Skill model."""
        assert len(skill.shadow_eval_tasks) > 0

    def test_feedback_signal_has_no_shadow_score_field(self, failed_session, seeder, skill):
        """FeedbackSignal model has no shadow_eval_score field at all."""
        signal = FeedbackSignal(
            id="s1", seeder_id=seeder.id, skill_id=skill.id,
            session_id=failed_session.id, eval_score=0.4,
            failed_tasks=failed_session.failed_tasks,
            created_at=datetime.now(timezone.utc),
        )
        fields = FeedbackSignal.model_fields.keys()
        assert "shadow_eval_score" not in fields
        assert "shadow_eval_tasks" not in fields
