"""no-op"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f1e2d3c4b5a6'
down_revision: Union[str, None] = '054afe0f5822'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # All tables and columns created in this migration are already present
    # in 000000000000_base_schema. This file is kept as a chain link only.
    pass


def downgrade() -> None:
    pass
