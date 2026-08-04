"""Earning opportunities — public browse (no auth).

Lets unauthenticated users discover pipeline-generated earning opportunities:
member jobs (clerks, verifiers, packers, certifiers, couriers), courier/bulking
deliver jobs and open supply aggregation campaigns.

Everything here is read-only. Participation goes through the existing
authenticated commerce endpoints (register detail, courier job actions), so no
new schema or action endpoints are introduced.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.earning_service import list_earning_opportunities

router = APIRouter(prefix="/earning", tags=["earning"])


@router.get("/opportunities")
async def api_earning_opportunities(
    page: int = Query(1, ge=1),
    kind: str | None = Query(
        None, pattern="^(pipeline_job|courier_job|supply)$"
    ),
    db: AsyncSession = Depends(get_db),
):
    return await list_earning_opportunities(db, page=page, kind=kind)
