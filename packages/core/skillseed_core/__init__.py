"""SkillSeed Core — protocol, models, registry, and evaluators."""

from skillseed_core.eval import KeywordEvaluator, SimpleEvaluator, SkillEvaluator, ThresholdEvaluator
from skillseed_core.models import (
    AgentProfile,
    CurriculumVersion,
    FeedbackSignal,
    LearningSession,
    Skill,
    SeederProfile,
)
from skillseed_core.protocol import (
    CritiqueLoopProtocol,
    PromptDistillationProtocol,
    SkillTransferProtocol,
    TraceDemonstrationProtocol,
)
from skillseed_core.registry import SkillRegistry

__all__ = [
    # models
    "Skill",
    "AgentProfile",
    "LearningSession",
    "SeederProfile",
    "FeedbackSignal",
    "CurriculumVersion",
    # protocol
    "SkillTransferProtocol",
    "PromptDistillationProtocol",
    "TraceDemonstrationProtocol",
    "CritiqueLoopProtocol",
    # registry
    "SkillRegistry",
    # eval
    "SkillEvaluator",
    "SimpleEvaluator",
    "KeywordEvaluator",
    "ThresholdEvaluator",
]

__version__ = "0.1.0"
