# File: alembic/versions/merge_heads_20250814.py | Version: 1.0 | Title: merge heads

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401

# revision identifiers, used by Alembic.
revision = "merge_20250814"
down_revision = (
    "0001_add_indexes",
    "016f77c94aa0",
)  # e.g., ("0001_add_indexes", "91677c79a0aa")
branch_labels = None
depends_on = None


def upgrade():
    # No-op: this revision only merges divergent history.
    pass


def downgrade():
    # Splitting merged history is not supported.
    pass
