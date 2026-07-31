"""Pydantic response schemas for key API endpoints.

Using explicit response_model declarations:
- Prevents accidental leakage of internal fields (hashed_password, totp_secret, etc.)
- Documents the API contract in Swagger UI / ReDoc
- Enables FastAPI response validation on outbound data
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


# ── Shared ─────────────────────────────────────────────────────────────────

class OKResponse(BaseModel):
    status: str


# ── Auth ───────────────────────────────────────────────────────────────────

class UserSummary(BaseModel):
    id: int
    email: str
    name: str
    role: str
    tenant_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserSummary


class MFARequiredResponse(BaseModel):
    requires_mfa: bool
    mfa_type: str
    temp_token: str


class UserDetailResponse(BaseModel):
    id: int
    email: str
    full_name: str
    company: str | None = None
    phone: str | None = None
    alternate_email: str | None = None
    alternate_phone: str | None = None
    role: str
    is_active: bool
    email_verified: bool
    phone_verified: bool = False
    totp_enabled: bool

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    users: list[dict[str, Any]]
    total: int
    page: int
    total_pages: int


# ── Monitoring ─────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    database: str
    timestamp: str


class SLAResponse(BaseModel):
    timestamp: str
    uptime_pct: float
    database_connected: bool
    total_requests_1h: int
    error_count_1h: int
    error_rate_pct_1h: float
    p95_latency_ms_1h: float
    error_budget_remaining_pct: float
    sla_target: str


class MetricsResponse(BaseModel):
    timestamp: str
    tables: dict[str, int]
    expiring_certificates: int
    unacknowledged_alerts: int
    active_recalls: int


# ── Suppliers ──────────────────────────────────────────────────────────────

class SupplierCreateResponse(BaseModel):
    id: int
    name: str


class ScorecardResponse(BaseModel):
    id: int
    overall_score: float | None = None


class SupplierRankEntry(BaseModel):
    supplier_id: int
    supplier_name: str
    overall_score: float | None = None
    period: str | None = None
    quality_score: float | None = None
    on_time_delivery_pct: float | None = None


class SupplierRankingResponse(BaseModel):
    ranking: list[SupplierRankEntry]


# ── Recalls ────────────────────────────────────────────────────────────────

class RecallCreateResponse(BaseModel):
    id: int
    status: str


class RecallStatusResponse(BaseModel):
    id: int
    status: str


# ── Insurance ──────────────────────────────────────────────────────────────

class PolicyCreateResponse(BaseModel):
    id: int
    policy_number: str


class ClaimCreateResponse(BaseModel):
    id: int
    status: str


class ClaimStatusResponse(BaseModel):
    id: int
    status: str


# ── ESG ────────────────────────────────────────────────────────────────────

class CarbonFootprintCreateResponse(BaseModel):
    id: int
    kg_co2e_per_kg: float


# ── Developer Portal ───────────────────────────────────────────────────────

class ApiKeyCreateResponse(BaseModel):
    id: int
    name: str
    api_key: str
    key_prefix: str
    rate_limit: int
    scopes: str | None = None


class ApiKeyListItem(BaseModel):
    id: int
    key_prefix: str
    name: str
    rate_limit: int | None = None
    scopes: str | None = None
    is_active: bool
    last_used_at: str | None = None
    created_at: str | None = None


class ApiKeyListResponse(BaseModel):
    api_keys: list[ApiKeyListItem]


class RevokeResponse(BaseModel):
    revoked: bool


# ── Retention ──────────────────────────────────────────────────────────────

class ArchivePolicyCreateResponse(BaseModel):
    id: int
    entity_type: str
    retention_days: int
