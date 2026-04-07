"""Shared configuration and helpers for MCP server tools."""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx

# The SkillSeed API base URL — defaults to localhost for development
SKILLSEED_API_URL = os.environ.get("SKILLSEED_API_URL", "http://localhost:8000")
SKILLSEED_API_KEY = os.environ.get("SKILLSEED_API_KEY", "")

# Persistent agent ID for this MCP session (stored in env or generated once)
_SESSION_AGENT_ID: str | None = None


def get_agent_id() -> str:
    """Return the persistent agent ID for this MCP session."""
    global _SESSION_AGENT_ID
    if _SESSION_AGENT_ID is None:
        _SESSION_AGENT_ID = os.environ.get("SKILLSEED_AGENT_ID", str(uuid.uuid4()))
    return _SESSION_AGENT_ID


@asynccontextmanager
async def get_http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Yield a configured async HTTP client for the SkillSeed API."""
    headers: dict[str, str] = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if SKILLSEED_API_KEY:
        headers["X-API-Key"] = SKILLSEED_API_KEY

    async with httpx.AsyncClient(
        base_url=SKILLSEED_API_URL,
        headers=headers,
        timeout=30.0,
    ) as client:
        yield client
