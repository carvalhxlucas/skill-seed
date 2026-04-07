<p align="center">
  <img src="./assets/banner.svg" alt="SkillSeed" width="100%"/>
</p>

<h1 align="center">SkillSeed</h1>

<p align="center">
  <strong>The npm for AI agent skills.</strong><br/>
  Plant a skill, watch it grow, seed the network.
</p>

<p align="center">
  <a href="https://github.com/carvalhxlucas/skill-seed/stargazers"><img src="https://img.shields.io/github/stars/carvalhxlucas/skill-seed?style=flat-square" alt="Stars"/></a>
  <a href="https://github.com/carvalhxlucas/skill-seed/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License"/></a>
  <a href="https://skillseed.dev/docs"><img src="https://img.shields.io/badge/docs-skillseed.dev-blue?style=flat-square" alt="Docs"/></a>
  <img src="https://img.shields.io/badge/status-early%20development-orange?style=flat-square" alt="Status"/>
</p>

---

## What is SkillSeed?

Today, when you want your AI agent to do something specific — query SQL, scrape the web, review code — you write the system prompt from scratch, test it, iterate, and hope it works.

**SkillSeed is a network where agents teach other agents.**

Specialist agents (*seeders*) share validated, benchmarked skills. Your agent (*grower*) learns from them in minutes — not days.

```python
from skillseed import SkillSeed

network = SkillSeed(api_key="...")
my_agent = network.enroll(agent=my_agent)

my_agent.learn("sql-expert")
my_agent.learn("web-scraper")

# your agent now knows SQL and web scraping
# validated, certified, ready to use
```

---

## How it works

```
Seeder (SQL expert) ──seeding──▶ Your agent ──▶ Bloomed skill
Seeder (SEO expert) ──seeding──▶ Your agent
```

**Three roles in the network:**

| Role | Can learn? | Can teach? | Requirement |
|---|---|---|---|
| Grower | ✅ | ❌ | Just sign up |
| Certified | ✅ | ✅ | Pass skill eval |
| Root Seeder | ✅ | ✅ | Curated by SkillSeed |

**How learning happens:**

1. Your agent receives the skill curriculum from a certified seeder
2. It attempts tasks based on that curriculum
3. An automated eval benchmarks performance before and after
4. If the eval passes, the skill is marked as **bloomed** on your agent

---

## Use it in Claude Code

```bash
claude mcp add skill-seed
```

Then just declare what your agent should know in `SKILL_SEED.md`:

```yaml
# SKILL_SEED.md
skills:
  - sql-expert
  - web-scraper
  - code-reviewer
```

Claude Code reads this file and your agent starts each session with all skills loaded. No manual setup.

---

## Use it via SDK

```bash
pip install skillseed
```
> ⚠️ Package not yet published. Follow the repo for updates.

```python
from skillseed import SkillSeed

network = SkillSeed(api_key="sk-...")

# enroll your agent
agent = network.enroll(agent=my_langchain_agent)

# learn a skill
agent.learn("sql-expert")

# list available skills
skills = network.registry.search("data analysis")

# contribute a skill (become a seeder)
network.seed(skill_name="pandas-expert", curriculum=my_curriculum)
```

---

## Use it via REST API

```http
POST /v1/agents/enroll
POST /v1/skills/learn
GET  /v1/skills/registry
GET  /v1/agents/{id}/skills
POST /v1/skills/seed
```

Works with any language, any framework — LangChain, LangGraph, CrewAI, AutoGen, custom.

---

## Skill Registry

Browse available skills at [skillseed.dev/registry](https://skillseed.dev/registry).

| Skill | Seeder | Learners | Status |
|---|---|---|---|
| `sql-expert` | @root | — | 🌱 coming soon |
| `web-scraper` | @root | — | 🌱 coming soon |
| `code-reviewer` | @root | — | 🌱 coming soon |

> Registry is being built. Star the repo to follow progress.

---

## Roadmap

- [ ] Core skill transfer protocol
- [ ] REST API
- [ ] Python SDK
- [ ] MCP Server (Claude Code integration)
- [ ] Skill Registry (public)
- [ ] Certified seeder program
- [ ] Skill versioning
- [ ] JS/TS SDK

---

## Contributing

SkillSeed is open-source and community-driven. Every skill in the network is a contribution.

```bash
git clone https://github.com/skill-seed/skill-seed
cd skill-seed
pip install -e ".[dev]"
```

See [CONTRIBUTING.md](./CONTRIBUTING.md) for how to propose new skills, improve the protocol, or build SDKs for other languages.

---

## Why open-source?

Because the network is only as strong as its community.

The more seeders contribute skills, the more valuable the network becomes for every grower. That only works if the protocol is open, auditable, and extensible by anyone.

---

## License

MIT © [SkillSeed](https://github.com/skill-seed)

---

<p align="center">
  <sub>Built for the AI agent ecosystem. Inspired by npm, PyPI, and the belief that agents should learn from each other.</sub>
</p>
