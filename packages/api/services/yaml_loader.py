"""YAML loader — reads skill definitions from .yaml files on disk."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import yaml

from skillseed_core.models import Skill

logger = logging.getLogger(__name__)

_DEFAULT_SEEDERS_PATH = Path(__file__).resolve().parents[3] / "seeders"


def _resolve_seeders_path() -> Path:
    raw = os.getenv("ROOT_SEEDER_PATH", str(_DEFAULT_SEEDERS_PATH))
    return Path(raw).resolve()


def _parse_eval_tasks(raw: list) -> list[str]:
    """Accept both plain strings and {task: ..., expected_concepts: [...]} dicts."""
    result = []
    for item in raw:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict) and "task" in item:
            result.append(item["task"])
    return result


def load_skills_from_directory(path: Path | None = None) -> list[Skill]:
    """Load all valid .yaml skill files from *path*.

    Files that fail validation are skipped with a warning so a single bad
    file never prevents the others from loading.
    """
    directory = path or _resolve_seeders_path()
    if not directory.exists():
        logger.warning("Seeders directory not found: %s", directory)
        return []

    skills: list[Skill] = []
    for yaml_file in sorted(directory.glob("*.yaml")):
        try:
            with yaml_file.open() as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                logger.warning("Skipping %s: expected a YAML mapping", yaml_file.name)
                continue

            # Normalise eval_tasks — YAML allows rich dicts, model wants strings
            if "eval_tasks" in data:
                data["eval_tasks"] = _parse_eval_tasks(data["eval_tasks"])

            # Drop YAML-only keys the model doesn't know about
            data.pop("eval_threshold", None)
            data.pop("seeder", None)

            skill = Skill.model_validate(data)
            skills.append(skill)
            logger.debug("Loaded skill '%s' from %s", skill.id, yaml_file.name)

        except Exception as exc:
            logger.warning("Skipping %s: %s", yaml_file.name, exc)

    logger.info("Loaded %d skill(s) from %s", len(skills), directory)
    return skills


def persist_skill_to_yaml(skill: Skill, path: Path | None = None) -> Path:
    """Write a Skill to a .yaml file in the seeders directory.

    Returns the path of the written file.
    """
    directory = path or _resolve_seeders_path()
    directory.mkdir(parents=True, exist_ok=True)

    yaml_file = directory / f"{skill.id}.yaml"
    data = {
        "id": skill.id,
        "name": skill.name,
        "version": skill.version,
        "category": skill.category,
        "description": skill.description,
        "curriculum": skill.curriculum,
        "eval_tasks": skill.eval_tasks,
        "seeder": {
            "is_root": False,
            "maintained_by": "community",
            "reputation_score": 0.0,
        },
    }

    with yaml_file.open("w") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    logger.info("Persisted skill '%s' to %s", skill.id, yaml_file)
    return yaml_file
