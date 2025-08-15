# File: /alembic/versions/20250814_add_views_table.py | Version: 1.2 | Title: Add views table (down_revision fixed to merge_20250814)
"""add views table"""

from alembic import op
import sqlalchemy as sa

# NOTE:
# Set `down_revision` to your actual current head.
# Based on your earlier merge, the head is `merge_20250814`.
# If your head differs, replace it accordingly and run `alembic upgrade head`.

revision = "add_views_20250814"
down_revision = "merge_20250814"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "views",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("scope_type", sa.String(), nullable=False),
        sa.Column("scope_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("filters_json", sa.JSON(), nullable=True),
        sa.Column("sort_spec", sa.String(), nullable=True),
        sa.Column("columns_json", sa.JSON(), nullable=True),
        sa.Column(
            "is_default", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_views_owner", "views", ["owner_id"])
    op.create_index("ix_views_scope", "views", ["scope_type", "scope_id"])


def downgrade():
    op.drop_index("ix_views_scope", table_name="views")
    op.drop_index("ix_views_owner", table_name="views")
    op.drop_table("views")
