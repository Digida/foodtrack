"""normalize users.role and users.user_type to lowercase enum values

The users.role (String(20)) and users.user_type (String(30)) columns have
accumulated mixed-case rows over time:

- server_default backfill wrote the enum VALUES in lowercase
  ('organization', 'viewer'), because that is the documented/app contract;
- later SAEnum binding wrote the enum member NAMES in uppercase
  ('ORGANIZATION', 'VIEWER').

SQLAlchemy's SAEnum (native_enum=False) validates against names by default, so
the lowercase backfilled rows raised a LookupError on load (breaking startup
seeding). The model now persists values via values_callable (lowercase). This
migration normalises existing rows to the same lowercase values so both the
old rows and the model agree. Because value == name.lower() for every member of
UserRole and UserType, a blanket lower() is exact and idempotent.

Revision ID: c7d8e9f0a1b2
Revises: 0ccfcee89224
Create Date: 2026-08-04
"""
from typing import Sequence, Union

from alembic import op

revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, None] = "0ccfcee89224"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE users SET role = lower(role), user_type = lower(user_type)")


def downgrade() -> None:
    op.execute("UPDATE users SET role = upper(role), user_type = upper(user_type)")
