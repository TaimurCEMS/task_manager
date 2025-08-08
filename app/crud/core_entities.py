# File: app/crud/core_entities.py | Version: 1.3 | Path: /app/crud/core_entities.py
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional

from app import models, schemas

# ----- WORKSPACE CRUD -----

def create_workspace(db: Session, data: schemas.core_entities.WorkspaceCreate, owner_id: str):
    """
    Create the workspace AND insert a WorkspaceMember record with Owner role.
    """
    try:
        new_workspace = models.core_entities.Workspace(
            name=data.name,
            owner_id=owner_id
        )
        db.add(new_workspace)
        db.commit()
        db.refresh(new_workspace)

        # Ensure membership is recorded per ERD (WorkspaceMembers link table)
        owner_membership = models.core_entities.WorkspaceMember(
            workspace_id=new_workspace.id,
            user_id=owner_id,
            role="Owner",
            is_active=True
        )
        db.add(owner_membership)
        db.commit()
        return new_workspace
    except Exception:
        db.rollback()
        raise

def get_workspace(db: Session, workspace_id: UUID):
    return db.query(models.core_entities.Workspace).filter_by(id=str(workspace_id), is_deleted=False).first()

def get_workspaces_for_user(db: Session, user_id: str):
    """
    Return all workspaces the user is a member of (any role), not only owned ones.
    """
    q = (
        db.query(models.core_entities.Workspace)
        .join(models.core_entities.WorkspaceMember, models.core_entities.Workspace.id == models.core_entities.WorkspaceMember.workspace_id)
        .filter(
            models.core_entities.WorkspaceMember.user_id == user_id,
            models.core_entities.WorkspaceMember.is_active == True,  # noqa: E712
            models.core_entities.Workspace.is_deleted == False        # noqa: E712
        )
        .distinct()
    )
    return q.all()

def update_workspace(db: Session, workspace_id: UUID, data: schemas.core_entities.WorkspaceUpdate):
    db_obj = get_workspace(db, workspace_id)
    if not db_obj:
        return None
    for field, value in data.dict(exclude_unset=True).items():
        setattr(db_obj, field, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def delete_workspace(db: Session, workspace_id: UUID):
    db_obj = get_workspace(db, workspace_id)
    if db_obj:
        db_obj.is_deleted = True
        db.commit()
    return db_obj

# ----- SPACE CRUD -----

def create_space(db: Session, data: schemas.core_entities.SpaceCreate):
    new_space = models.core_entities.Space(**data.dict())
    db.add(new_space)
    db.commit()
    db.refresh(new_space)
    return new_space

def get_space(db: Session, space_id: UUID):
    return db.query(models.core_entities.Space).filter_by(id=str(space_id), is_deleted=False).first()

def get_spaces_by_workspace(db: Session, workspace_id: str):
    return db.query(models.core_entities.Space).filter_by(workspace_id=workspace_id, is_deleted=False).all()

def update_space(db: Session, space_id: UUID, data: schemas.core_entities.SpaceUpdate):
    db_obj = get_space(db, space_id)
    if not db_obj:
        return None
    for field, value in data.dict(exclude_unset=True).items():
        setattr(db_obj, field, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def delete_space(db: Session, space_id: UUID):
    db_obj = get_space(db, space_id)
    if db_obj:
        db_obj.is_deleted = True
        db.commit()
    return db_obj

# ----- FOLDER CRUD -----

def create_folder(db: Session, data: schemas.core_entities.FolderCreate):
    new_folder = models.core_entities.Folder(**data.dict())
    db.add(new_folder)
    db.commit()
    db.refresh(new_folder)
    return new_folder

def get_folder(db: Session, folder_id: UUID):
    return db.query(models.core_entities.Folder).filter_by(id=str(folder_id), is_deleted=False).first()

def get_folders_by_space(db: Session, space_id: str):
    return db.query(models.core_entities.Folder).filter_by(space_id=space_id, is_deleted=False).all()

def update_folder(db: Session, folder_id: UUID, data: schemas.core_entities.FolderUpdate):
    db_obj = get_folder(db, folder_id)
    if not db_obj:
        return None
    for field, value in data.dict(exclude_unset=True).items():
        setattr(db_obj, field, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def delete_folder(db: Session, folder_id: UUID):
    db_obj = get_folder(db, folder_id)
    if db_obj:
        db_obj.is_deleted = True
        db.commit()
    return db_obj

# ----- LIST CRUD -----

def create_list(db: Session, data: schemas.core_entities.ListCreate):
    new_list = models.core_entities.List(**data.dict())
    db.add(new_list)
    db.commit()
    db.refresh(new_list)
    return new_list

def get_list(db: Session, list_id: UUID):
    return db.query(models.core_entities.List).filter_by(id=str(list_id), is_deleted=False).first()

def get_lists_by_space(db: Session, space_id: str):
    return db.query(models.core_entities.List).filter_by(space_id=space_id, is_deleted=False).all()

def get_lists_by_folder(db: Session, folder_id: str):
    return db.query(models.core_entities.List).filter_by(folder_id=folder_id, is_deleted=False).all()

def update_list(db: Session, list_id: UUID, data: schemas.core_entities.ListUpdate):
    db_obj = get_list(db, list_id)
    if not db_obj:
        return None
    for field, value in data.dict(exclude_unset=True).items():
        setattr(db_obj, field, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def delete_list(db: Session, list_id: UUID):
    db_obj = get_list(db, list_id)
    if db_obj:
        db_obj.is_deleted = True
        db.commit()
    return db_obj
