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
│   │   │   ├── models.py              # Skill, Agent, SeederProfile, LearningSession
│   │   │   ├── protocol.py            # SkillTransferProtocol (abstract base)
│   │   │   ├── registry.py            # SkillRegistry (in-memory + interface)
│   │   │   └── eval.py                # SkillEvaluator (base class)
│   │   └── tests/
│   │       └── test_models.py
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
│   │   │   └── eval_service.py        # runs evals and certifies skills
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

class AgentProfile(BaseModel):
    id: str
    name: str
    framework: str             # "langchain" | "langgraph" | "custom" | etc
    bloomed_skills: list[str]  # skill ids the agent has learned

class LearningSession(BaseModel):
    id: str
    agent_id: str
    skill_id: str
    status: Literal["pending", "learning", "evaluating", "bloomed", "failed"]
    started_at: datetime
    completed_at: datetime | None
    eval_score: float | None   # 0.0 to 1.0
    learned_state: dict        # system prompt delta, memory injections, etc

class SeederProfile(BaseModel):
    id: str
    skill_id: str
    agent_id: str
    reputation_score: float    # based on how many agents bloomed from this seeder
    total_learners: int
    is_root: bool              # True = curated by SkillSeed team
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

### Step 3 — REST API (`packages/api`)

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
```

Use **async FastAPI**, **Pydantic v2**, **PostgreSQL** (via asyncpg or SQLAlchemy async) for persistence, **Redis** for session state during learning.

---

### Step 4 — Python SDK (`packages/sdk-python`)

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
```

---

### Step 5 — MCP Server (`packages/mcp-server`)

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

### Step 6 — Root Seeder definitions (`seeders/`)

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
eval_threshold: 0.7
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
```

---

## Key design principles

1. **Protocol-first** — the skill transfer protocol is the core abstraction. Everything else is infrastructure around it.
2. **Eval-gated** — a skill is only "bloomed" if it passes the automated benchmark. No fake certifications.
3. **Framework-agnostic** — the SDK works with LangChain, LangGraph, CrewAI, AutoGen, or any custom agent.
4. **MCP-native** — Claude Code is a first-class citizen. The MCP server should feel seamless.
5. **Open protocol** — the skill transfer protocol and YAML schema are public specs. Anyone can implement a compatible seeder.

---

## Start here

1. Create the monorepo structure above
2. Implement `packages/core` first — models, protocol base class, registry interface
3. Write tests for the models before moving to the API
4. Then build the API, SDK, and MCP server in that order
5. Keep each package independently installable via pip

Ask me before making architectural decisions not covered in this document.
