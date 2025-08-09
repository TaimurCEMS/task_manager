# File: /app/models/core_entities.py | Version: 1.5 | Path: /app/models/core_entities.py
from __future__ import annotations

from datetime import datetime, UTC
from typing import List as TList, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


def gen_uuid() -> str:
    return str(uuid4())


class User(Base):
    __tablename__ = "user"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    comments: Mapped[TList["Comment"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    time_entries: Mapped[TList["TimeEntry"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    task_assignees: Mapped[TList["TaskAssignee"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    workspaces: Mapped[TList["WorkspaceMember"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    task_watchers: Mapped[TList["TaskWatcher"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Workspace(Base):
    __tablename__ = "workspace"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[str] = mapped_column(ForeignKey("user.id"), nullable=False)

    owner: Mapped["User"] = relationship()
    spaces: Mapped[TList["Space"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    members: Mapped[TList["WorkspaceMember"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")


class WorkspaceMember(Base):
    __tablename__ = "workspace_member"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="member")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    workspace: Mapped["Workspace"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="workspaces")


class Space(Base):
    __tablename__ = "space"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True, nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)

    workspace: Mapped["Workspace"] = relationship(back_populates="spaces")
    folders: Mapped[TList["Folder"]] = relationship(back_populates="space", cascade="all, delete-orphan")
    lists: Mapped[TList["List"]] = relationship(back_populates="space", cascade="all, delete-orphan")


class Folder(Base):
    __tablename__ = "folder"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    space_id: Mapped[str] = mapped_column(ForeignKey("space.id"), index=True, nullable=False)

    space: Mapped["Space"] = relationship(back_populates="folders")
    lists: Mapped[TList["List"]] = relationship(back_populates="folder", cascade="all, delete-orphan")


class List(Base):
    __tablename__ = "list"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    space_id: Mapped[str] = mapped_column(ForeignKey("space.id"), index=True, nullable=False)
    folder_id: Mapped[Optional[str]] = mapped_column(ForeignKey("folder.id"), index=True)

    space: Mapped["Space"] = relationship(back_populates="lists")
    folder: Mapped[Optional["Folder"]] = relationship(back_populates="lists")
    tasks: Mapped[TList["Task"]] = relationship(back_populates="list", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "task"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    list_id: Mapped[str] = mapped_column(ForeignKey("list.id"), index=True, nullable=False)
    parent_task_id: Mapped[Optional[str]] = mapped_column(ForeignKey("task.id"), index=True, nullable=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="to_do")
    priority: Mapped[Optional[str]] = mapped_column(String(20))
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    list: Mapped["List"] = relationship(back_populates="tasks")
    parent: Mapped[Optional["Task"]] = relationship("Task", remote_side=lambda: [Task.id], back_populates="children")
    children: Mapped[TList["Task"]] = relationship("Task", back_populates="parent", cascade="all, delete-orphan")

    comments: Mapped[TList["Comment"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    time_entries: Mapped[TList["TimeEntry"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    assignees: Mapped[TList["TaskAssignee"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    tags: Mapped[TList["TaskTag"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    watchers: Mapped[TList["TaskWatcher"]] = relationship(back_populates="task", cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "comment"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    task_id: Mapped[str] = mapped_column(ForeignKey("task.id"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    user: Mapped["User"] = relationship(back_populates="comments")
    task: Mapped["Task"] = relationship(back_populates="comments")


class TimeEntry(Base):
    __tablename__ = "time_entry"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    task_id: Mapped[str] = mapped_column(ForeignKey("task.id"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    minutes: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    user: Mapped["User"] = relationship(back_populates="time_entries")
    task: Mapped["Task"] = relationship(back_populates="time_entries")


class TaskAssignee(Base):
    __tablename__ = "task_assignee"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    task_id: Mapped[str] = mapped_column(ForeignKey("task.id"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="task_assignees")
    task: Mapped["Task"] = relationship(back_populates="assignees")


# ---- Tags ----
class Tag(Base):
    __tablename__ = "tag"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspace.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(20))

    tasks: Mapped[TList["TaskTag"]] = relationship(back_populates="tag", cascade="all, delete-orphan")


class TaskTag(Base):
    __tablename__ = "task_tag"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    task_id: Mapped[str] = mapped_column(ForeignKey("task.id"), index=True, nullable=False)
    tag_id: Mapped[str] = mapped_column(ForeignKey("tag.id"), index=True, nullable=False)

    task: Mapped["Task"] = relationship(back_populates="tags")
    tag: Mapped["Tag"] = relationship(back_populates="tasks")


# ---- Watchers ----
class TaskWatcher(Base):
    __tablename__ = "task_watcher"
    __table_args__ = (UniqueConstraint("task_id", "user_id", name="uq_task_watcher_task_user"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    task_id: Mapped[str] = mapped_column(ForeignKey("task.id"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    task: Mapped["Task"] = relationship(back_populates="watchers")
    user: Mapped["User"] = relationship(back_populates="task_watchers")


# Helpful composite index for comment listing
Index("ix_comment_task_id_created_at", Comment.task_id, Comment.created_at)
