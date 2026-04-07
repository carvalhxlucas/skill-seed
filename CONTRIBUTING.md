# Contributing to SkillSeed

Thank you for your interest in contributing to SkillSeed. This document explains how to get started, how to add new seeders, and how to implement new transfer protocols.

---

## Getting started

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (for running postgres and redis locally)
- `pip` or `uv` for package management

### Install the monorepo

```bash
git clone https://github.com/skillseed/skill-seed.git
cd skill-seed
make install-dev
```

This installs all packages in editable mode with development dependencies.

### Run the test suite

```bash
make test
```

All tests run without external services. No `OPENAI_API_KEY` or database is required.

### Start the dev server

```bash
make dev
```

This spins up postgres and redis via Docker Compose, then starts the API on `http://localhost:8000`.

---

## Project structure

```
packages/
├── core/          # Protocol, models, registry, evaluators (no framework deps)
├── api/           # FastAPI REST API
├── sdk-python/    # Python SDK (thin HTTP wrapper)
└── mcp-server/    # FastMCP server for Claude Code
seeders/           # Root seeder YAML definitions
```

Each package is independently installable via `pip install -e packages/<name>`.

---

## How to add a new Root Seeder

Root seeders are the authoritative source of truth for a skill. They are maintained by the SkillSeed team and live in `seeders/`.

### 1. Create a YAML file

Add a new file to `seeders/` following the schema:

```yaml
id: my-skill-id          # URL-safe, lowercase, hyphen-separated
name: My Skill Name
version: 1.0.0           # semver
category: engineering    # data | automation | engineering | community | etc
description: >
  One or two sentences describing what this skill teaches.
  What will the agent be able to do after learning it?

curriculum:
  - "Task 1 the seeder uses to teach the skill"
  - "Task 2 — be specific and actionable"
  - "Task 3 — cover the breadth of the skill"

eval_tasks:
  - task: "A benchmark task the grower must complete"
    expected_concepts: ["concept-a", "concept-b"]
  - task: "Another evaluation task"
    expected_concepts: ["concept-c"]

eval_threshold: 0.7      # 0.0–1.0, recommend 0.7 for most skills

seeder:
  is_root: true
  maintained_by: skillseed-team
  reputation_score: 5.0
```

### 2. Test your seeder

```bash
# Verify the YAML is valid
python -c "import yaml; yaml.safe_load(open('seeders/my-skill-id.yaml'))"

# Register it in the API and test a learning session
make dev
curl -X POST http://localhost:8000/v1/agents/enroll \
  -H 'Content-Type: application/json' \
  -d '{"name": "test-bot", "framework": "custom"}'
```

### 3. Open a pull request

- One YAML file per PR for new seeders
- Include a brief description of why this skill is valuable
- Ensure `eval_tasks` cover the key concepts from `curriculum`

---

## How to implement a new transfer protocol

Transfer protocols live in `packages/core/skillseed/protocol.py`.

### 1. Subclass `SkillTransferProtocol`

```python
class MyNewProtocol(SkillTransferProtocol):
    async def transfer(
        self,
        skill: Skill,
        seeder: SeederProfile,
        grower: AgentProfile,
    ) -> LearningSession:
        # Your implementation here
        ...
```

### 2. Implement the `transfer` method

The method must:
- Create a `LearningSession` with a fresh UUID
- Set `status` to `"learning"` while in progress
- Transition to `"evaluating"` when running the eval
- Set `eval_score` (0.0–1.0)
- Mark as `"bloomed"` if `eval_score >= threshold`, otherwise `"failed"`
- Populate `learned_state` with any artifacts (system prompts, memory injections, etc.)
- Set `completed_at` when done

### 3. Add tests

All protocols must have tests in `packages/core/tests/test_models.py`. Tests must run without external services — stub any LLM calls.

### 4. Export from `__init__.py`

Add your new protocol to `packages/core/skillseed/__init__.py`:

```python
from skillseed.protocol import MyNewProtocol
__all__ = [..., "MyNewProtocol"]
```

---

## Pull request guidelines

- Keep PRs focused — one feature or fix per PR
- All tests must pass (`make test`)
- No lint errors (`make lint`)
- Add or update tests for any changed behavior
- Update the relevant `pyproject.toml` version for breaking changes
- Write clear commit messages in the imperative mood: "Add X", "Fix Y", "Update Z"

---

## Code style

- Python 3.11+ syntax (`X | None`, not `Optional[X]`)
- Pydantic v2 style (`model_config`, `model_validate`, `model_dump`)
- `async def` / `await` throughout — no sync blocking calls
- `ruff` for formatting and linting
- `mypy` for type checking (strict mode on core package)
- Docstrings on all public classes and methods

---

## Reporting issues

Open a GitHub issue with:
- A clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Python version and OS

---

## Code of Conduct

Be respectful, constructive, and collaborative. We follow the [Contributor Covenant](https://www.contributor-covenant.org/).
