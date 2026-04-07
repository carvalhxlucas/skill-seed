# SkillSeed — Project Bootstrap

You are bootstrapping **SkillSeed**, an open-source network where AI agents teach and learn skills from each other.

Think of it as **npm for AI agent skills** — specialist agents (seeders) share validated, benchmarked capabilities, and other agents (growers) learn from them in minutes.

---

## Core concepts

| Term | Meaning |
|---|---|
| **Skill** | A validated capability an agent can learn (e.g. `sql-expert`, `web-scraper`) |
| **Seeder** | An agent that teaches a skill to others |
| **Grower** | An agent that learns skills from seeders |
| **Seeding** | The process of transferring a skill from seeder to grower |
| **Bloomed skill** | A skill that passed the automated eval after learning |
| **Root Seeder** | Curated, trusted seeders maintained by the SkillSeed team |
| **Garden** | The full network of agents and skills |
| **Feedback signal** | The eval result sent back to the seeder after each learning session |
| **Curriculum revision** | When a seeder updates its teaching based on accumulated feedback signals |
| **Shadow eval** | A reserved set of eval tasks never exposed to seeders — used to prevent teaching-to-the-test |
| **Reputation score** | A seeder's score based on the bloom rate of its learners over time |

---

## Project structure to create

```
skill-seed/
├── README.md                          # already written, do not overwrite
├── CONTRIBUTING.md
├── LICENSE                            # MIT
├── CLAUDE.md                          # this file
├── assets/
│   └── banner.svg
│
├── packages/
│   ├── core/                          # protocol and shared types
│   │   ├── pyproject.toml
│   │   ├── skillseed/
│   │   │   ├── __init__.py
│   │   │   ├── models.py              # Skill, Agent, SeederProfile, LearningSession, FeedbackSignal
│   │   │   ├── protocol.py            # SkillTransferProtocol (abstract base)
│   │   │   ├── registry.py            # SkillRegistry (in-memory + interface)
│   │   │   ├── eval.py                # SkillEvaluator (base class) + ShadowEval
│   │   │   └── evolution.py           # SeederEvolution — feedback loop + curriculum revision
│   │   └── tests/
│   │       ├── test_models.py
│   │       └── test_evolution.py
│   │
│   ├── api/                           # REST API (FastAPI)
│   │   ├── pyproject.toml
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── agents.py              # POST /v1/agents/enroll, GET /v1/agents/{id}/skills
│   │   │   ├── skills.py              # GET /v1/skills/registry, POST /v1/skills/learn
│   │   │   └── seed.py                # POST /v1/skills/seed
│   │   ├── services/
│   │   │   ├── learning_service.py    # orchestrates the seeding protocol
│   │   │   ├── eval_service.py        # runs evals and certifies skills
│   │   │   └── evolution_service.py   # sends feedback signals + triggers curriculum revision
│   │   └── tests/
│   │       └── test_routers.py
│   │
│   ├── sdk-python/                    # Python SDK
│   │   ├── pyproject.toml
│   │   ├── skillseed/
│   │   │   ├── __init__.py
│   │   │   ├── client.py              # SkillSeed(api_key) main entrypoint
│   │   │   ├── agent.py               # EnrolledAgent with .learn() and .seed()
│   │   │   └── registry.py            # registry.search(), registry.list()
│   │   └── tests/
│   │       └── test_client.py
│   │
│   └── mcp-server/                    # MCP Server for Claude Code
│       ├── pyproject.toml
│       ├── server.py                  # FastMCP server entrypoint
│       ├── tools/
│       │   ├── search_skills.py       # search_skills(query) → list of skills
│       │   ├── learn_skill.py         # learn_skill(skill_id) → learning result
│       │   ├── get_my_skills.py       # get_my_skills() → enrolled agent skills
│       │   └── seed_skill.py          # seed_skill(skill_data) → seeder profile
│       └── tests/
│           └── test_tools.py
│
├── seeders/                           # Root Seeder definitions (YAML)
│   ├── sql-expert.yaml
│   ├── web-scraper.yaml
│   └── code-reviewer.yaml
│
├── docker-compose.yml                 # postgres + redis + api
├── .env.example
└── Makefile                           # make dev, make test, make lint
```

---

## What to build first (MVP order)

### Step 1 — Core models (`packages/core`)

Create the foundational data models. Keep them simple, typed, and framework-agnostic.

```python
# models.py — key types to implement

class Skill(BaseModel):
    id: str                    # e.g. "sql-expert"
    name: str
    description: str
    version: str               # semver
    category: str
    curriculum: list[str]      # list of tasks the seeder uses to teach
    eval_tasks: list[str]      # tasks used to benchmark the grower
    shadow_eval_tasks: list[str]  # NEVER exposed to seeders — anti-gaming protection

class AgentProfile(BaseModel):
    id: str
    name: str
    framework: str             # "langchain" | "langgraph" | "custom" | etc
    bloomed_skills: list[str]  # skill ids the agent has learned

class LearningSession(BaseModel):
    id: str
    agent_id: str
    skill_id: str
    seeder_id: str
    status: Literal["pending", "learning", "evaluating", "bloomed", "failed"]
    started_at: datetime
    completed_at: datetime | None
    eval_score: float | None        # 0.0 to 1.0 (public eval)
    shadow_eval_score: float | None # 0.0 to 1.0 (shadow eval — not shown to seeder)
    failed_tasks: list[str]         # which eval tasks the grower failed
    learned_state: dict             # system prompt delta, memory injections, etc

class FeedbackSignal(BaseModel):
    id: str
    seeder_id: str
    skill_id: str
    session_id: str
    eval_score: float               # public score only — shadow score never sent
    failed_tasks: list[str]         # tasks the grower failed
    grower_responses: dict          # task → grower's actual response
    created_at: datetime

class CurriculumVersion(BaseModel):
    id: str
    skill_id: str
    seeder_id: str
    version: str                    # semver — bumped on each revision
    curriculum: list[str]
    revision_reason: str            # why this revision was made
    avg_bloom_rate: float | None    # tracked after rollout
    created_at: datetime

class SeederProfile(BaseModel):
    id: str
    skill_id: str
    agent_id: str
    reputation_score: float         # based on bloom rate of learners over time
    total_learners: int
    bloom_rate: float               # % of growers who bloomed with this seeder
    curriculum_version: str         # current semver of the curriculum
    is_root: bool                   # True = curated by SkillSeed team
    evolution_enabled: bool         # whether this seeder auto-revises curriculum
```

---

### Step 2 — Skill Transfer Protocol (`packages/core/protocol.py`)

The protocol defines HOW a seeder teaches a grower. Start with **prompt distillation** as the first method — simplest to implement, lowest cost, good enough for MVP.

```python
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
    The grower's system prompt is updated with the distilled knowledge.
    
    Flow:
    1. Load skill curriculum
    2. Call LLM to generate an expert system prompt for this skill
    3. Run eval tasks against the grower with the new prompt
    4. If eval_score >= threshold → mark as bloomed
    5. Return LearningSession with learned_state containing the new prompt
    """
    threshold: float = 0.7
```

Future protocols to stub (not implement yet):
- `TraceDemonstrationProtocol` — seeder executes, grower observes
- `CritiqueLoopProtocol` — grower attempts, seeder corrects iteratively

---

### Step 3 — Seeder Self-Improvement (`packages/core/evolution.py`)

This is the layer that makes SkillSeed different from a static skill marketplace. Seeders autonomously improve their curriculum based on accumulated feedback from learners.

**Three levels of evolution — implement in order:**

**Level 1 — Reactive improvement** (implement first)

After every failed session, a `FeedbackSignal` is sent to the seeder. The seeder uses it to revise weak parts of the curriculum.

```python
class SeederEvolution:
    """
    Manages the self-improvement loop for a seeder.
    Triggered automatically after each LearningSession completes.
    """

    async def on_session_complete(self, session: LearningSession) -> None:
        """
        Called after every session — bloomed or failed.
        If score < revision_threshold, generate and store a FeedbackSignal.
        """
        if session.eval_score < self.revision_threshold:
            signal = FeedbackSignal(
                seeder_id=session.seeder_id,
                skill_id=session.skill_id,
                session_id=session.id,
                eval_score=session.eval_score,        # public score only
                failed_tasks=session.failed_tasks,
                grower_responses=session.learned_state.get("responses", {}),
            )
            await self.store_signal(signal)
            await self.maybe_revise(session.seeder_id, session.skill_id)

    async def maybe_revise(self, seeder_id: str, skill_id: str) -> CurriculumVersion | None:
        """
        Revise the curriculum if enough failure signals have accumulated.
        Default: revise after 5 failures or when bloom_rate drops below 0.6.
        Calls LLM to generate an improved curriculum based on failure patterns.
        Returns a new CurriculumVersion if revision happened, None otherwise.
        """
        ...
```

**Level 2 — Proactive improvement** (implement second)

Instead of waiting for failures, the seeder periodically analyzes patterns across all sessions to find weak spots before they cause failures.

```python
    async def analyze_failure_patterns(
        self,
        seeder_id: str,
        skill_id: str,
        last_n: int = 100,
    ) -> list[WeakSpot]:
        """
        Scans the last N sessions and identifies which curriculum tasks
        correlate with low eval scores. Returns a ranked list of weak spots.
        Example: "CTEs appear in 80% of failed sessions → strengthen that task"
        """
        ...

    async def strengthen_curriculum(
        self,
        seeder_id: str,
        weak_spots: list[WeakSpot],
    ) -> CurriculumVersion:
        """
        Calls LLM with the current curriculum + weak spots to generate
        a revised curriculum that better prepares growers for those tasks.
        Saves as a new CurriculumVersion with bumped semver.
        """
        ...
```

**Level 3 — Cross-seeder learning** (stub only, implement later)

High-performing seeders can share their teaching approach with lower-performing seeders of different skills.

```python
    async def cross_pollinate(
        self,
        source_seeder_id: str,   # high bloom rate seeder
        target_seeder_id: str,   # low bloom rate seeder, different skill
    ) -> None:
        """
        Extracts teaching patterns from the source seeder's curriculum history
        and applies analogous improvements to the target seeder.
        STUB — do not implement in MVP. Design the interface only.
        """
        ...
```

**Shadow eval — anti-gaming protection**

The shadow eval tasks are stored separately and never included in the `FeedbackSignal` sent to seeders. Only the public `eval_score` and `failed_tasks` from the public eval are shared. This prevents seeders from teaching directly to the test.

```python
class ShadowEval:
    """
    Runs alongside the public eval but results are NEVER sent to the seeder.
    Used internally to validate that the public bloom rate is not inflated.
    If shadow_eval_score < public eval_score by more than 0.2, flag the seeder
    for review — it may be teaching to the test.
    """
    drift_threshold: float = 0.2
```

---

### Step 4 — REST API (`packages/api`)

FastAPI app. Keep it minimal for MVP.

**Endpoints to implement:**

```
POST /v1/agents/enroll
  body: { name, framework }
  returns: AgentProfile

GET  /v1/agents/{agent_id}/skills
  returns: list[BloomedSkill]

GET  /v1/skills/registry
  query params: ?category=&search=
  returns: list[Skill]

POST /v1/skills/learn
  body: { agent_id, skill_id }
  returns: LearningSession

GET  /v1/skills/learn/{session_id}
  returns: LearningSession (for polling status)

POST /v1/skills/seed
  body: { agent_id, skill } 
  returns: SeederProfile

GET  /v1/seeders/{seeder_id}/feedback
  returns: list[FeedbackSignal]

GET  /v1/seeders/{seeder_id}/curriculum/history
  returns: list[CurriculumVersion]

POST /v1/seeders/{seeder_id}/evolve
  body: { force: bool }        # force a revision even if threshold not met
  returns: CurriculumVersion | null
```

Use **async FastAPI**, **Pydantic v2**, **PostgreSQL** (via asyncpg or SQLAlchemy async) for persistence, **Redis** for session state during learning.

---

### Step 5 — Python SDK (`packages/sdk-python`)

Thin wrapper around the REST API. DX is everything here — make it feel like the simplest possible interface.

```python
# Target usage — this is the DX to optimize for

from skillseed import SkillSeed

ss = SkillSeed(api_key="sk-...")

# enroll
agent = ss.enroll(name="my-assistant", framework="langchain")

# learn
session = agent.learn("sql-expert")  # blocks until bloomed or failed
print(session.status)                # "bloomed"
print(session.learned_state)         # dict with system_prompt_delta etc

# list skills
skills = ss.registry.search("data")

# become a seeder
ss.seed(agent_id=agent.id, skill=my_skill_definition)

# check your seeder feedback
seeder = ss.seeders.get(seeder_id="...")
signals = seeder.feedback(last_n=50)

# trigger curriculum revision manually
new_version = seeder.evolve()
print(new_version.revision_reason)   # why the LLM revised it
print(new_version.version)           # e.g. "1.2.0"
```

---

### Step 6 — MCP Server (`packages/mcp-server`)

FastMCP server exposing 4 tools for Claude Code.

```python
# Tools to implement:

@mcp.tool()
async def search_skills(query: str) -> list[dict]:
    """Search available skills in the SkillSeed network."""

@mcp.tool()
async def learn_skill(skill_id: str, agent_id: str) -> dict:
    """Start a learning session for the given skill."""

@mcp.tool()
async def get_my_skills(agent_id: str) -> list[dict]:
    """List all bloomed skills for a given agent."""

@mcp.tool()
async def seed_skill(skill_name: str, description: str, curriculum: list[str]) -> dict:
    """Contribute a new skill to the network."""
```

Also implement **SKILL_SEED.md auto-detection**: when Claude Code starts a session, the MCP server checks for a `SKILL_SEED.md` in the project root and auto-calls `learn_skill` for each declared skill.

---

### Step 7 — Root Seeder definitions (`seeders/`)

Define the first 3 root seeders as YAML. These are the source of truth for each skill.

```yaml
# seeders/sql-expert.yaml
id: sql-expert
name: SQL Expert
version: 1.0.0
category: data
description: >
  Teaches an agent to write efficient, correct SQL queries.
  Covers SELECT, JOIN, aggregation, subqueries, and query optimization.
curriculum:
  - "Write a query to find the top 5 customers by total order value"
  - "Write a query using a LEFT JOIN between orders and customers"
  - "Optimize a slow query by rewriting it with a CTE"
  - "Write a query to calculate a 7-day rolling average"
eval_tasks:
  - task: "Find all users who placed more than 3 orders in the last 30 days"
    expected_concepts: ["GROUP BY", "HAVING", "date filtering"]
  - task: "Write a query to detect duplicate email addresses in a users table"
    expected_concepts: ["GROUP BY", "HAVING COUNT > 1"]
shadow_eval_tasks:
  - task: "Write a recursive CTE to build an employee hierarchy from a self-referencing table"
    expected_concepts: ["WITH RECURSIVE", "self-join", "depth traversal"]
  - task: "Rewrite a correlated subquery as a window function"
    expected_concepts: ["OVER", "PARTITION BY", "ROW_NUMBER or RANK"]
eval_threshold: 0.7
evolution:
  enabled: true
  revision_threshold: 0.6     # bloom rate below this triggers revision
  min_signals_to_revise: 5    # minimum feedback signals before first revision
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| API framework | FastAPI + Pydantic v2 |
| Database | PostgreSQL (asyncpg) |
| Cache / sessions | Redis |
| MCP Server | FastMCP |
| LLM calls | OpenAI SDK (model-agnostic interface) |
| Testing | pytest + pytest-asyncio |
| Linting | ruff + mypy |
| Containerization | Docker + docker-compose |

---

## Environment variables

```env
# .env.example
SKILLSEED_API_KEY=sk-...
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/skillseed
REDIS_URL=redis://localhost:6379
EVAL_THRESHOLD=0.7
ROOT_SEEDER_PATH=./seeders
EVOLUTION_REVISION_THRESHOLD=0.6
EVOLUTION_MIN_SIGNALS=5
SHADOW_EVAL_DRIFT_THRESHOLD=0.2
```

---

## Key design principles

1. **Protocol-first** — the skill transfer protocol is the core abstraction. Everything else is infrastructure around it.
2. **Eval-gated** — a skill is only "bloomed" if it passes the automated benchmark. No fake certifications.
3. **Framework-agnostic** — the SDK works with LangChain, LangGraph, CrewAI, AutoGen, or any custom agent.
4. **MCP-native** — Claude Code is a first-class citizen. The MCP server should feel seamless.
5. **Open protocol** — the skill transfer protocol and YAML schema are public specs. Anyone can implement a compatible seeder.
6. **Self-improving seeders** — seeders autonomously revise their curriculum based on learner feedback. The network gets smarter over time without manual intervention.
7. **Shadow eval integrity** — shadow eval tasks are never exposed to seeders under any circumstance, including via API, SDK, or logs. This is non-negotiable.
8. **Curriculum versioning** — every revision creates a new `CurriculumVersion`. Never mutate in place. This allows rollback and A/B comparison between versions.

---

## Start here

1. Create the monorepo structure above
2. Implement `packages/core` first — models, protocol base class, registry interface
3. Implement `evolution.py` — Level 1 (reactive) only for MVP
4. Write tests for models and evolution before moving to the API
5. Then build the API, SDK, and MCP server in that order
6. Keep each package independently installable via pip
7. Never expose `shadow_eval_tasks` in any public-facing response

Ask me before making architectural decisions not covered in this document.
