# File: app/models/custom_fields.py | Version: 1.1 | Path: app/models/custom_fields.py
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.core_entities import Workspace

from typing import Any
from typing import List as TList
from typing import Optional

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.core_entities import List as ListModel
from app.models.core_entities import Task, gen_uuid


class CustomFieldDefinition(Base):
    __tablename__ = "custom_field_definition"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_workspace_field_name"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspace.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    field_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # e.g. 'Text', 'Number', 'Dropdown'
    options: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON
    )  # For dropdown options, etc.

    workspace: Mapped["Workspace"] = relationship()
    enabled_on_lists: Mapped[TList["ListCustomField"]] = relationship(
        back_populates="field_definition", cascade="all, delete-orphan"
    )


class ListCustomField(Base):
    __tablename__ = "list_custom_field"
    __table_args__ = (
        UniqueConstraint(
            "list_id", "field_definition_id", name="uq_list_field_definition"
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    list_id: Mapped[str] = mapped_column(
        ForeignKey("list.id"), index=True, nullable=False
    )
    field_definition_id: Mapped[str] = mapped_column(
        ForeignKey("custom_field_definition.id"), index=True, nullable=False
    )

    list_entity: Mapped["ListModel"] = relationship()
    field_definition: Mapped["CustomFieldDefinition"] = relationship(
        back_populates="enabled_on_lists"
    )


class CustomFieldValue(Base):
    __tablename__ = "custom_field_value"
    __table_args__ = (
        UniqueConstraint("task_id", "field_definition_id", name="uq_task_field_value"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    task_id: Mapped[str] = mapped_column(
        ForeignKey("task.id"), index=True, nullable=False
    )
    field_definition_id: Mapped[str] = mapped_column(
        ForeignKey("custom_field_definition.id"), index=True, nullable=False
    )
    value: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    task: Mapped["Task"] = relationship()
    field_definition: Mapped["CustomFieldDefinition"] = relationship()
