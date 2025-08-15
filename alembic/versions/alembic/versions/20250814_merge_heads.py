# File: alembic/versions/20250814_merge_heads.py | Version: 1.0 | Path: /alembic/versions/20250814_merge_heads.py
# Purpose: merge the two Alembic heads shown in CI so `alembic upgrade head` has a single target

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401

# revision identifiers, used by Alembic.
revision = "merge_20250814"
down_revision = ("0001_add_indexes", "91677c79a0aa")  # <-- from your CI log
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No schema changes; this revision only merges divergent history.
    pass


def downgrade() -> None:
    # Splitting a merge is not supported.
    pass
