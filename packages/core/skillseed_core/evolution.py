"""Seeder self-improvement — feedback loop, curriculum revision, shadow eval."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from skillseed_core.models import (
    CurriculumVersion,
    FeedbackSignal,
    LearningSession,
    SeederProfile,
    Skill,
)


# ---------------------------------------------------------------------------
# WeakSpot — identified failure pattern in a curriculum task
# ---------------------------------------------------------------------------

@dataclass
class WeakSpot:
    """A curriculum task that correlates with grower failures."""

    task: str
    failure_rate: float     # 0.0–1.0: proportion of sessions where this task appeared in failed_tasks
    session_count: int      # how many sessions were analysed


# ---------------------------------------------------------------------------
# ShadowEval — anti-gaming integrity check
# ---------------------------------------------------------------------------

class ShadowEval:
    """Runs a secondary eval on shadow tasks that are never exposed to seeders.

    Purpose: detect if a seeder is teaching directly to the public eval tasks
    (teaching-to-the-test). If the shadow score lags significantly behind the
    public score, the seeder is flagged for review.

    The shadow_eval_score is stored on LearningSession but is NEVER included
    in FeedbackSignal or any public API response.
    """

    drift_threshold: float = 0.2

    def __init__(self, drift_threshold: float = 0.2) -> None:
        self.drift_threshold = drift_threshold

    async def evaluate(self, session: LearningSession, skill: Skill) -> float:
        """Score the session against the shadow eval tasks.

        Stub implementation for MVP — returns a score slightly below the public
        eval score to simulate realistic drift without requiring a live LLM.
        """
        if not skill.shadow_eval_tasks:
            return session.eval_score or 0.0

        # Stub: shadow score is 90% of public eval score by default.
        # Real implementation calls an LLM with shadow tasks and grades responses.
        public_score = session.eval_score or 0.0
        return round(public_score * 0.9, 3)

    def is_suspicious(self, public_score: float, shadow_score: float) -> bool:
        """Return True if the gap between public and shadow score exceeds the threshold.

        A large gap suggests the seeder may be teaching to the public test tasks.
        """
        return (public_score - shadow_score) >= self.drift_threshold


# ---------------------------------------------------------------------------
# SeederEvolution — three-level self-improvement loop
# ---------------------------------------------------------------------------

class SeederEvolution:
    """Manages the self-improvement loop for a seeder.

    Level 1 — Reactive: triggered after each failed session.
    Level 2 — Proactive: analyses patterns across many sessions.
    Level 3 — Cross-seeder: stub only; not implemented in MVP.
    """

    def __init__(
        self,
        revision_threshold: float = 0.6,
        min_signals_to_revise: int = 5,
        shadow_eval: ShadowEval | None = None,
    ) -> None:
        self.revision_threshold = revision_threshold
        self.min_signals_to_revise = min_signals_to_revise
        self._shadow_eval = shadow_eval or ShadowEval()

    # ------------------------------------------------------------------
    # Level 1 — Reactive improvement
    # ------------------------------------------------------------------

    async def on_session_complete(
        self,
        session: LearningSession,
        seeder: SeederProfile,
        skill: Skill,
        signals: list[FeedbackSignal],
        versions: list[CurriculumVersion],
    ) -> FeedbackSignal | None:
        """Called after every session — bloomed or failed.

        If the eval score is below the revision threshold, creates a
        FeedbackSignal and potentially triggers a curriculum revision.

        Returns the FeedbackSignal if one was created, else None.
        """
        if session.eval_score is None:
            return None

        # Run shadow eval and store on session (never sent to seeder)
        session.shadow_eval_score = await self._shadow_eval.evaluate(session, skill)

        if session.eval_score >= self.revision_threshold:
            return None  # session passed — no feedback needed

        signal = FeedbackSignal(
            id=str(uuid.uuid4()),
            seeder_id=seeder.id,
            skill_id=skill.id,
            session_id=session.id,
            eval_score=session.eval_score,   # public score only — shadow never sent
            failed_tasks=list(session.failed_tasks),
            grower_responses=session.learned_state.get("responses", {}),
            created_at=datetime.now(timezone.utc),
        )
        signals.append(signal)

        await self.maybe_revise(seeder, skill, signals, versions)
        return signal

    async def maybe_revise(
        self,
        seeder: SeederProfile,
        skill: Skill,
        signals: list[FeedbackSignal],
        versions: list[CurriculumVersion],
    ) -> CurriculumVersion | None:
        """Revise the curriculum if enough failure signals have accumulated.

        Triggers when:
        - At least `min_signals_to_revise` signals exist, AND
        - The seeder's bloom_rate has dropped below `revision_threshold`.

        Returns a new CurriculumVersion if a revision occurred, None otherwise.
        """
        seeder_signals = [s for s in signals if s.seeder_id == seeder.id]

        if len(seeder_signals) < self.min_signals_to_revise:
            return None

        if seeder.bloom_rate > self.revision_threshold:
            return None

        # Identify weak spots from accumulated signals
        weak_spots = await self.analyze_failure_patterns(seeder_signals, skill)
        if not weak_spots:
            return None

        return await self.strengthen_curriculum(seeder, skill, weak_spots, versions)

    # ------------------------------------------------------------------
    # Level 2 — Proactive improvement
    # ------------------------------------------------------------------

    async def analyze_failure_patterns(
        self,
        signals: list[FeedbackSignal],
        skill: Skill,
        last_n: int = 100,
    ) -> list[WeakSpot]:
        """Scan the last N feedback signals and identify weak curriculum tasks.

        Returns tasks ranked by failure rate (highest first).
        Example: "CTEs appear in 80% of failed sessions → strengthen that task".
        """
        recent = signals[-last_n:]
        if not recent:
            return []

        task_failures: dict[str, int] = {}
        for signal in recent:
            for task in signal.failed_tasks:
                task_failures[task] = task_failures.get(task, 0) + 1

        total = len(recent)
        weak_spots = [
            WeakSpot(
                task=task,
                failure_rate=round(count / total, 3),
                session_count=total,
            )
            for task, count in task_failures.items()
        ]
        weak_spots.sort(key=lambda w: w.failure_rate, reverse=True)
        return weak_spots

    async def strengthen_curriculum(
        self,
        seeder: SeederProfile,
        skill: Skill,
        weak_spots: list[WeakSpot],
        versions: list[CurriculumVersion],
    ) -> CurriculumVersion:
        """Generate a revised curriculum that addresses identified weak spots.

        Calls LLM in production. For MVP/stub, adds reinforcement tasks for
        each weak spot directly to the curriculum.

        Saves as a new CurriculumVersion with bumped semver.
        Never mutates the curriculum in-place — always creates a new version.
        """
        weak_tasks = [w.task for w in weak_spots[:3]]  # focus on top 3

        # Stub: prepend reinforcement tasks for each weak spot
        reinforcements = [
            f"[Reinforcement] Practice: {task}" for task in weak_tasks
        ]
        new_curriculum = reinforcements + list(skill.curriculum)

        # Bump minor version
        parts = seeder.curriculum_version.split(".")
        new_version = f"{parts[0]}.{int(parts[1]) + 1}.0"

        reason = (
            f"Reactive revision: growers failed on {len(weak_tasks)} task(s): "
            + ", ".join(f'"{t}"' for t in weak_tasks)
        )

        version = CurriculumVersion(
            id=str(uuid.uuid4()),
            skill_id=skill.id,
            seeder_id=seeder.id,
            version=new_version,
            curriculum=new_curriculum,
            revision_reason=reason,
            created_at=datetime.now(timezone.utc),
        )

        versions.append(version)
        seeder.curriculum_version = new_version
        skill.curriculum = new_curriculum

        return version

    # ------------------------------------------------------------------
    # Level 3 — Cross-seeder learning (stub — not implemented in MVP)
    # ------------------------------------------------------------------

    async def cross_pollinate(
        self,
        source_seeder: SeederProfile,
        target_seeder: SeederProfile,
    ) -> None:
        """Extract teaching patterns from a high-performing seeder and apply
        analogous improvements to a lower-performing seeder of a different skill.

        Not implemented in MVP. Design interface only.
        """
        raise NotImplementedError(
            "cross_pollinate is not implemented in MVP. "
            "Implement after Level 1 and Level 2 are validated in production."
        )
