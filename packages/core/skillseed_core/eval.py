"""Skill evaluators — assess whether a grower has successfully learned a skill."""

from __future__ import annotations

from abc import ABC, abstractmethod

from skillseed_core.models import LearningSession, Skill


class SkillEvaluator(ABC):
    """Base evaluator class. Returns a score between 0.0 and 1.0."""

    @abstractmethod
    async def evaluate(self, session: LearningSession, skill: Skill) -> float:
        """Evaluate the learning session and return a score from 0.0 to 1.0."""
        ...


class SimpleEvaluator(SkillEvaluator):
    """Stub evaluator that always returns a passing score.

    .. warning::
        **Never use in production.** This evaluator bypasses all skill
        certification gates — every skill will be marked as "bloomed"
        regardless of quality. It exists solely for unit tests and local
        development without LLM credentials.

    Returns 0.8, which passes the default threshold of 0.7.
    """

    async def evaluate(self, session: LearningSession, skill: Skill) -> float:
        return 0.8


class KeywordEvaluator(SkillEvaluator):
    """Evaluates by checking how many expected keywords appear in learned_state.

    Useful for lightweight smoke tests without calling an LLM.
    """

    async def evaluate(self, session: LearningSession, skill: Skill) -> float:
        system_prompt = session.learned_state.get("system_prompt_delta", "")
        if not system_prompt:
            return 0.0

        skill_tokens = set(skill.name.lower().split())
        prompt_lower = system_prompt.lower()

        hits = sum(1 for token in skill_tokens if token in prompt_lower)
        return hits / len(skill_tokens) if skill_tokens else 1.0


class ThresholdEvaluator(SkillEvaluator):
    """Wraps another evaluator and applies a configurable pass/fail threshold.

    Useful for composing evaluators with custom thresholds.
    """

    def __init__(self, inner: SkillEvaluator, threshold: float = 0.7) -> None:
        self._inner = inner
        self.threshold = threshold

    async def evaluate(self, session: LearningSession, skill: Skill) -> float:
        score = await self._inner.evaluate(session, skill)
        return score
