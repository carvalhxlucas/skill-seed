"""EvalService — runs skill evaluations and certifies (blooms) learning sessions."""

from __future__ import annotations

from datetime import datetime, timezone

from skillseed_core.eval import SimpleEvaluator, SkillEvaluator
from skillseed_core.models import LearningSession, Skill


class EvalService:
    """Orchestrates skill evaluation and marks sessions as bloomed or failed."""

    def __init__(
        self,
        evaluator: SkillEvaluator | None = None,
        threshold: float = 0.7,
    ) -> None:
        self._evaluator = evaluator or SimpleEvaluator()
        self.threshold = threshold

    async def evaluate_session(
        self,
        session: LearningSession,
        skill: Skill,
    ) -> LearningSession:
        """Run the evaluator on a session and update its status.

        Returns the mutated session (bloomed or failed).
        """
        session.status = "evaluating"

        score = await self._evaluator.evaluate(session, skill)
        session.eval_score = score
        session.completed_at = datetime.now(timezone.utc)

        if score >= self.threshold:
            session.status = "bloomed"
        else:
            session.status = "failed"

        return session

    def is_passing(self, score: float) -> bool:
        """Return True if the score meets the bloom threshold."""
        return score >= self.threshold
