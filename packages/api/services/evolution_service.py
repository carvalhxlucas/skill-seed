"""EvolutionService — manages feedback signals and curriculum revision for seeders."""

from __future__ import annotations

import os

from skillseed_core.evolution import SeederEvolution, ShadowEval
from skillseed_core.models import (
    CurriculumVersion,
    FeedbackSignal,
    LearningSession,
    SeederProfile,
    Skill,
)


class EvolutionService:
    """Orchestrates the seeder self-improvement loop.

    Stores feedback signals and curriculum versions in memory for MVP.
    Replace with PostgreSQL for production.
    """

    def __init__(self) -> None:
        revision_threshold = float(os.environ.get("EVOLUTION_REVISION_THRESHOLD", "0.6"))
        min_signals = int(os.environ.get("EVOLUTION_MIN_SIGNALS", "5"))
        drift_threshold = float(os.environ.get("SHADOW_EVAL_DRIFT_THRESHOLD", "0.2"))

        self._evolution = SeederEvolution(
            revision_threshold=revision_threshold,
            min_signals_to_revise=min_signals,
            shadow_eval=ShadowEval(drift_threshold=drift_threshold),
        )

        # In-memory stores
        self._signals: list[FeedbackSignal] = []
        self._versions: list[CurriculumVersion] = []

    # ------------------------------------------------------------------
    # Session hook — call this after every learning session
    # ------------------------------------------------------------------

    async def on_session_complete(
        self,
        session: LearningSession,
        seeder: SeederProfile,
        skill: Skill,
    ) -> FeedbackSignal | None:
        """Process a completed session: run shadow eval, maybe create feedback signal."""
        return await self._evolution.on_session_complete(
            session=session,
            seeder=seeder,
            skill=skill,
            signals=self._signals,
            versions=self._versions,
        )

    # ------------------------------------------------------------------
    # Manual evolve — force a curriculum revision
    # ------------------------------------------------------------------

    async def evolve(
        self,
        seeder: SeederProfile,
        skill: Skill,
        force: bool = False,
    ) -> CurriculumVersion | None:
        """Trigger a curriculum revision for a seeder.

        If force=True, bypasses the min_signals_to_revise threshold.
        """
        if force:
            weak_spots = await self._evolution.analyze_failure_patterns(
                signals=[s for s in self._signals if s.seeder_id == seeder.id],
                skill=skill,
            )
            if not weak_spots:
                # No failure data — add a generic improvement pass
                from skillseed_core.evolution import WeakSpot
                weak_spots = [WeakSpot(task=skill.curriculum[0], failure_rate=0.0, session_count=0)]

            return await self._evolution.strengthen_curriculum(
                seeder=seeder,
                skill=skill,
                weak_spots=weak_spots,
                versions=self._versions,
            )

        return await self._evolution.maybe_revise(
            seeder=seeder,
            skill=skill,
            signals=self._signals,
            versions=self._versions,
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_signals(self, seeder_id: str, last_n: int | None = None) -> list[FeedbackSignal]:
        """Return feedback signals for a seeder. Never includes shadow_eval_score."""
        signals = [s for s in self._signals if s.seeder_id == seeder_id]
        if last_n:
            signals = signals[-last_n:]
        return signals

    def get_curriculum_history(self, seeder_id: str) -> list[CurriculumVersion]:
        """Return all curriculum versions for a seeder, oldest first."""
        return [v for v in self._versions if v.seeder_id == seeder_id]
