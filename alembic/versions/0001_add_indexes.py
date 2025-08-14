# File: alembic/versions/0001_add_indexes.py | Version: 1.0 | Title: Add helpful indexes for performance
from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_add_indexes"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # task
    from sqlalchemy import inspect as __insp, text as __text  # safe if duplicated  __bind = op.get_bind() __name = op.f("ix_task_list_id") if __bind.dialect.name == "sqlite":     op.execute(__text(f"CREATE INDEX IF NOT EXISTS {__name} ON task (list_id)")) else:     if __name not in { i["name"] for i in __insp(__bind).get_indexes("task") }:         op.create_index(__name, "task", ["list_id"], unique=False)
    op.create_index("ix_task_status", "task", ["status"], unique=False)
    op.create_index("ix_task_created_at", "task", ["created_at"], unique=False)

    # tag mapping
    op.create_index(
        "ix_task_tag_task_id_tag_id", "task_tag", ["task_id", "tag_id"], unique=False
    )

    # custom field value lookup
    op.create_index(
        "ix_custom_field_value_task_field",
        "custom_field_value",
        ["task_id", "field_definition_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_custom_field_value_task_field", table_name="custom_field_value")
    op.drop_index("ix_task_tag_task_id_tag_id", table_name="task_tag")
    op.drop_index("ix_task_created_at", table_name="task")
    op.drop_index("ix_task_status", table_name="task")
    op.drop_index("ix_task_list_id", table_name="task")
