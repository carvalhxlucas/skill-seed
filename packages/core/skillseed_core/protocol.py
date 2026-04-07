"""Skill transfer protocols — defines HOW a seeder teaches a grower."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone


from skillseed_core.models import AgentProfile, LearningSession, Skill, SeederProfile


class SkillTransferProtocol(ABC):
    """Base class for all teaching methods."""

    @abstractmethod
    async def transfer(
        self,
        skill: Skill,
        seeder: SeederProfile,
        grower: AgentProfile,
    ) -> LearningSession:
        """Execute the skill transfer and return a session with learned_state."""
        ...


class PromptDistillationProtocol(SkillTransferProtocol):
    """
    Seeder generates an optimized system prompt for the grower.

    Flow:
    1. Load skill curriculum
    2. Call LLM to generate an expert system prompt for this skill
    3. Run eval tasks against the grower with the new prompt
    4. If eval_score >= threshold → mark as bloomed
    5. Return LearningSession with learned_state containing the new prompt
    """

    def __init__(self, threshold: float = 0.7, llm_client=None) -> None:
        self.threshold = threshold
        self._llm_client = llm_client  # optional — None triggers stub

    async def transfer(
        self,
        skill: Skill,
        seeder: SeederProfile,
        grower: AgentProfile,
    ) -> LearningSession:
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        session = LearningSession(
            id=session_id,
            agent_id=grower.id,
            skill_id=skill.id,
            seeder_id=seeder.id,
            status="learning",
            started_at=now,
        )

        # Step 1: generate expert system prompt
        system_prompt = await self._generate_system_prompt(skill)

        # Step 2: transition to evaluating
        session.status = "evaluating"

        # Step 3: run a simple keyword-coverage eval over eval_tasks
        eval_score = await self._evaluate(skill, system_prompt)
        session.eval_score = eval_score

        # Step 4: determine outcome
        if eval_score >= self.threshold:
            session.status = "bloomed"
            if skill.id not in grower.bloomed_skills:
                grower.bloomed_skills.append(skill.id)
        else:
            session.status = "failed"

        session.completed_at = datetime.now(timezone.utc)

        # Identify which eval tasks the grower failed (stub: mark last task if score is low)
        if eval_score < self.threshold and skill.eval_tasks:
            session.failed_tasks = [skill.eval_tasks[-1]]

        session.learned_state = {
            "system_prompt_delta": system_prompt,
            "skill_id": skill.id,
            "eval_score": eval_score,
        }

        return session

    async def _generate_system_prompt(self, skill: Skill) -> str:
        """Generate an expert system prompt for the skill.

        In production this calls an LLM. For MVP / testing, returns a deterministic stub.
        """
        if self._llm_client is not None:
            return await self._call_llm(skill)

        # Deterministic stub — safe for tests without OPENAI_API_KEY
        curriculum_text = "\n".join(f"- {task}" for task in skill.curriculum)
        return (
            f"You are an expert in {skill.name}. "
            f"{skill.description.strip()}\n\n"
            f"Your teaching curriculum covers:\n{curriculum_text}\n\n"
            f"Always provide accurate, well-structured answers based on this expertise."
        )

    async def _call_llm(self, skill: Skill) -> str:
        """Call the LLM client to generate a system prompt. Override in production."""
        raise NotImplementedError("LLM client integration not implemented in base class.")

    async def _evaluate(self, skill: Skill, system_prompt: str) -> float:
        """Simple heuristic eval: check that the prompt references key skill terms."""
        if not skill.eval_tasks:
            return 1.0

        skill_keywords = [word.lower() for word in skill.name.split()]
        prompt_lower = system_prompt.lower()

        hits = sum(1 for kw in skill_keywords if kw in prompt_lower)
        coverage = hits / len(skill_keywords) if skill_keywords else 1.0

        # Clamp to a reasonable passing range for stubs
        return min(max(coverage, 0.0), 1.0) if coverage < 0.7 else 0.85


class TraceDemonstrationProtocol(SkillTransferProtocol):
    """
    Seeder executes tasks while the grower observes traces.

    Not implemented in MVP — stub only.
    """

    async def transfer(
        self,
        skill: Skill,
        seeder: SeederProfile,
        grower: AgentProfile,
    ) -> LearningSession:
        raise NotImplementedError(
            "TraceDemonstrationProtocol is not implemented yet. "
            "Use PromptDistillationProtocol for MVP."
        )


class CritiqueLoopProtocol(SkillTransferProtocol):
    """
    Grower attempts tasks; seeder provides iterative critique.

    Not implemented in MVP — stub only.
    """

    async def transfer(
        self,
        skill: Skill,
        seeder: SeederProfile,
        grower: AgentProfile,
    ) -> LearningSession:
        raise NotImplementedError(
            "CritiqueLoopProtocol is not implemented yet. "
            "Use PromptDistillationProtocol for MVP."
        )
