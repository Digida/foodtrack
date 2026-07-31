"""
Startup / readiness routes.

GET /api/v1/startup/status
    Returns live migration and seeding progress. Safe to poll.
    Never requires authentication — the frontend needs it before login exists.

GET /api/v1/startup/ready
    Minimal liveness check: 200 OK once all startup tasks are done,
    503 while still initialising.  Suitable for polling scripts and UX loaders.

GET /api/v1/startup/section/{section}
    Returns whether a specific seed section (e.g. "GRAINS", "SEAFOOD") is ready.
    Endpoint handlers can use this to return descriptive 503s to the user.
"""

from fastapi import APIRouter, HTTPException
from app.services.startup_service import (
    get_startup_status,
    is_section_ready,
    require_section_ready,
)

router = APIRouter(prefix="/startup", tags=["startup"])


@router.get("/status")
async def api_startup_status():
    """
    Full startup progress report.

    Response fields
    ---------------
    ready           — true once migrations + seeding are both complete
    phase           — pending | migrating | seeding | done | error
    migration       — Alembic state: current revision, head, detail
    seeding         — per-section progress with expected / seeded / missing counts
    errors          — list of any errors encountered (empty on success)
    uptime_seconds  — seconds since the process started this task
    """
    return get_startup_status()


@router.get("/ready")
async def api_startup_ready():
    """
    Minimal readiness check.

    Returns 200 {"ready": true} once all startup tasks complete.
    Returns 503 {"ready": false, ...} while still initialising.

    The frontend can poll this endpoint and show a progress indicator
    until it receives 200.
    """
    status = get_startup_status()
    if status["ready"]:
        return {"ready": True, "phase": "done"}
    raise HTTPException(
        status_code=503,
        detail={
            "ready":   False,
            "phase":   status["phase"],
            "message": "Platform is initialising — migrations and seeding in progress.",
            "seeding": {
                "total_inserted": status["seeding"]["total_inserted"],
                "sections_done": sum(
                    1 for s in status["seeding"]["sections"].values()
                    if s["status"] == "done"
                ),
                "sections_total": len(status["seeding"]["sections"]),
            },
        },
    )


@router.get("/section/{section}")
async def api_section_ready(section: str):
    """
    Check whether a specific seed section is ready.

    If the section is still initialising, returns 503 with a human-readable
    message suitable for surfacing in the UI:

        {
          "error":   "data_not_ready",
          "section": "SEAFOOD",
          "status":  "running",
          "message": "The 'SEAFOOD' dataset is still being initialised ..."
        }

    If ready, returns:

        { "section": "SEAFOOD", "ready": true }
    """
    section = section.upper()
    err = require_section_ready(section)
    if err:
        raise HTTPException(status_code=503, detail=err)
    return {"section": section, "ready": True}
