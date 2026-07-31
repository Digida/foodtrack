"""no-op"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '577747fbe587'
down_revision: Union[str, None] = '267c1a1c4a4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # All tables and columns created in this migration are already present
    # in 000000000000_base_schema. This file is kept as a chain link only.
    pass


def downgrade() -> None:
    pass
