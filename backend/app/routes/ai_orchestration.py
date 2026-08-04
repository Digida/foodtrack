from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.utils.dependencies import get_current_user
from app.services.ai_orchestration_service import (
    orchestrate_task, tool_catalog, pipeline_catalog,
    list_memories, clear_memories,
)

router = APIRouter(prefix="/ai", tags=["ai"])


class OrchestrateRequest(BaseModel):
    task: str
    context: dict | None = None


class ExecuteToolRequest(BaseModel):
    tool: str
    args: dict | None = None


@router.post("/orchestrate")
async def api_orchestrate(
    req: OrchestrateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a natural-language task via MAG -> DAG -> RAG -> fallback."""
    try:
        return await orchestrate_task(db, user, req.task, req.context)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tools")
async def api_tool_catalog(
    user: User = Depends(get_current_user),
):
    """Catalog of all 40 orchestratable tools."""
    return tool_catalog()


@router.post("/tools/execute")
async def api_execute_tool(
    req: ExecuteToolRequest,
    user: User = Depends(get_current_user),
):
    """Invoke a single codified tool directly with explicit arguments."""
    import asyncio

    from agent.tool_registry import registry

    if not registry.has(req.tool):
        raise HTTPException(status_code=404, detail=f"Unknown tool: {req.tool}")
    loop = asyncio.get_running_loop()
    args = req.args or {}
    try:
        result = await loop.run_in_executor(None, lambda: registry.execute(req.tool, **args))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"tool": req.tool, "result": result}


@router.get("/pipelines")
async def api_pipeline_catalog(
    user: User = Depends(get_current_user),
):
    """Catalog of the DAG pipelines available to the orchestrator."""
    return pipeline_catalog()


@router.get("/memories")
async def api_list_memories(
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Persisted MAG memory episodes for the current user."""
    return {"memories": await list_memories(db, user, limit)}


@router.delete("/memories")
async def api_clear_memories(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Clear the current user's persisted MAG memory episodes."""
    removed = await clear_memories(db, user)
    return {"removed": removed}
