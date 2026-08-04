"""AI orchestration service — bridges the agent orchestrator to the API layer.

Runs the MAG -> DAG -> RAG -> fallback regression inside a worker thread (the
tools' ``execute`` methods spin up their own event loop via ``asyncio.run``,
which cannot run on the request's event loop) and persists resolved episodes to
the ``AiMemory`` table for durability across restarts.
"""
from __future__ import annotations

import asyncio

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.orchestrator import orchestrator
from agent.pipelines import get_pipelines
from agent.tool_registry import registry
from app.models.ai_memory import AiMemory, MemoryStrategy
from app.models.user import User

_PERSIST_STRATEGIES = {"mag", "dag", "fallback"}


async def orchestrate_task(
    db: AsyncSession,
    user: User,
    task: str,
    context: dict | None = None,
) -> dict:
    task = (task or "").strip()
    if not task:
        raise ValueError("task is required")

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        orchestrator.orchestrate,
        task,
        context or {},
    )
    await _persist_memory(db, user, task, result)
    return result


async def _persist_memory(db: AsyncSession, user: User, task: str, result: dict) -> None:
    strategy = result.get("strategy")
    if strategy not in _PERSIST_STRATEGIES:
        return

    recipe: list[dict] = []
    if strategy == "mag":
        recipe = [
            {"tool": s.get("tool"), "args": s.get("args", {})}
            for s in result.get("steps", [])
        ]
    elif strategy == "dag":
        recipe = [
            {"tool": out.get("tool"), "args": out.get("args", {})}
            for out in result.get("outputs", {}).values()
        ]
    elif strategy == "fallback" and result.get("tool"):
        recipe = [{"tool": result["tool"], "args": {}}]

    recipe = [r for r in recipe if r.get("tool")]
    if not recipe:
        return

    tags = [strategy]
    if strategy == "dag" and result.get("pipeline"):
        tags.append(result["pipeline"])
    if strategy == "fallback" and result.get("tool"):
        tags.append(result["tool"])

    memory = AiMemory(
        user_id=user.id,
        task=task,
        strategy=MemoryStrategy(strategy),
        recipe=recipe,
        summary=result.get("answer", "")[:500] or None,
        tags=tags,
        confidence=result.get("confidence"),
        hits=0,
    )
    db.add(memory)
    await db.commit()


def tool_catalog() -> dict:
    return {
        "count": registry.count(),
        "tools": registry.list_tools(),
    }


def pipeline_catalog() -> dict:
    return {
        "count": len(get_pipelines()),
        "pipelines": get_pipelines(),
    }


async def list_memories(db: AsyncSession, user: User, limit: int = 50) -> list[dict]:
    rows = (
        await db.execute(
            select(AiMemory)
            .where(AiMemory.user_id == user.id)
            .order_by(AiMemory.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [serialize_memory(m) for m in rows]


async def clear_memories(db: AsyncSession, user: User) -> int:
    result = await db.execute(delete(AiMemory).where(AiMemory.user_id == user.id))
    await db.commit()
    return result.rowcount or 0


def serialize_memory(memory: AiMemory) -> dict:
    return {
        "id": memory.id,
        "task": memory.task,
        "strategy": memory.strategy.value if isinstance(memory.strategy, MemoryStrategy) else memory.strategy,
        "recipe": memory.recipe,
        "summary": memory.summary,
        "tags": memory.tags or [],
        "confidence": memory.confidence,
        "hits": memory.hits,
        "created_at": memory.created_at.isoformat() if memory.created_at else None,
    }
