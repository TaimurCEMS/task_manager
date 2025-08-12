# File: /tests/test_db_indexes.py | Version: 1.1 | Path: /tests/test_db_indexes.py
from sqlalchemy import inspect
from sqlalchemy.engine import Engine


def _idx_names(engine: Engine, table_name: str) -> set[str]:
    insp = inspect(engine)
    return {i["name"] for i in insp.get_indexes(table_name)}


def test_expected_indexes_exist(db_session):
    engine = db_session.get_bind()
    insp = inspect(engine)
    tables = set(insp.get_table_names())

    # task: single-column indexes come from index=True on columns
    task_idx = _idx_names(engine, "task")
    assert "ix_task_list_id" in task_idx
    assert "ix_task_parent_task_id" in task_idx

    # task_dependency: only check if table exists in this build
    if "task_dependency" in tables:
        dep_idx = _idx_names(engine, "task_dependency")
        assert "ix_task_dependency_task_id" in dep_idx
        assert "ix_task_dependency_depends_on_task_id" in dep_idx

    # comment: composite index we added explicitly
    comment_idx = _idx_names(engine, "comment")
    assert "ix_comment_task_id_created_at" in comment_idx
