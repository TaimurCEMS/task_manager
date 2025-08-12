# File: /app/crud/core_entities.py | Version: 1.6 | Path: /app/crud/core_entities.py
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import core_entities as models
from app.schemas import core_entities as schema

# ----- WORKSPACE CRUD -----


def create_workspace(db: Session, data: schema.WorkspaceCreate, owner_id: str):
    """
    Create the workspace AND insert a WorkspaceMember record with Owner role.
    """
    try:
        new_workspace = models.Workspace(
            name=data.name,
            owner_id=owner_id,
        )
        db.add(new_workspace)
        db.commit()
        db.refresh(new_workspace)

        # Ensure membership is recorded per ERD (WorkspaceMember link)
        owner_membership = models.WorkspaceMember(
            workspace_id=new_workspace.id,
            user_id=owner_id,
            role="Owner",
            is_active=True,
        )
        db.add(owner_membership)
        db.commit()
        return new_workspace
    except Exception:
        db.rollback()
        raise


def get_workspace(db: Session, workspace_id: UUID):
    q = db.query(models.Workspace).filter_by(id=str(workspace_id))
    if hasattr(models.Workspace, "is_deleted"):
        q = q.filter(models.Workspace.is_deleted == False)  # noqa: E712
    return q.first()


def get_workspaces_for_user(db: Session, user_id: str):
    """
    Return all workspaces the user is a member of (any role), not only owned ones.
    """
    q = (
        db.query(models.Workspace)
        .join(
            models.WorkspaceMember,
            models.Workspace.id == models.WorkspaceMember.workspace_id,
        )
        .filter(
            models.WorkspaceMember.user_id == user_id,
            models.WorkspaceMember.is_active == True,  # noqa: E712
        )
        .distinct()
    )
    if hasattr(models.Workspace, "is_deleted"):
        q = q.filter(models.Workspace.is_deleted == False)  # noqa: E712
    return q.all()


def update_workspace(db: Session, workspace_id: UUID, data: schema.WorkspaceUpdate):
    db_obj = get_workspace(db, workspace_id)
    if not db_obj:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(db_obj, field, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_workspace(db: Session, workspace_id: UUID):
    db_obj = get_workspace(db, workspace_id)
    if not db_obj:
        return None
    # Soft delete if supported; otherwise hard delete
    if hasattr(db_obj, "is_deleted"):
        setattr(db_obj, "is_deleted", True)
        db.commit()
    else:
        db.delete(db_obj)
        db.commit()
    return db_obj


# ----- SPACE CRUD -----


def create_space(db: Session, data: schema.SpaceCreate):
    new_space = models.Space(**data.model_dump())
    db.add(new_space)
    db.commit()
    db.refresh(new_space)
    return new_space


def get_space(db: Session, space_id: UUID):
    q = db.query(models.Space).filter_by(id=str(space_id))
    if hasattr(models.Space, "is_deleted"):
        q = q.filter(models.Space.is_deleted == False)  # noqa: E712
    return q.first()


def get_spaces_by_workspace(db: Session, workspace_id: str):
    q = db.query(models.Space).filter_by(workspace_id=workspace_id)
    if hasattr(models.Space, "is_deleted"):
        q = q.filter(models.Space.is_deleted == False)  # noqa: E712
    return q.all()


def update_space(db: Session, space_id: UUID, data: schema.SpaceUpdate):
    db_obj = get_space(db, space_id)
    if not db_obj:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(db_obj, field, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_space(db: Session, space_id: UUID):
    db_obj = get_space(db, space_id)
    if not db_obj:
        return None
    if hasattr(db_obj, "is_deleted"):
        db_obj.is_deleted = True
        db.commit()
    else:
        db.delete(db_obj)
        db.commit()
    return db_obj


# ----- FOLDER CRUD -----


def create_folder(db: Session, data: schema.FolderCreate):
    new_folder = models.Folder(**data.model_dump())
    db.add(new_folder)
    db.commit()
    db.refresh(new_folder)
    return new_folder


def get_folder(db: Session, folder_id: UUID):
    q = db.query(models.Folder).filter_by(id=str(folder_id))
    if hasattr(models.Folder, "is_deleted"):
        q = q.filter(models.Folder.is_deleted == False)  # noqa: E712
    return q.first()


def get_folders_by_space(db: Session, space_id: str):
    q = db.query(models.Folder).filter_by(space_id=space_id)
    if hasattr(models.Folder, "is_deleted"):
        q = q.filter(models.Folder.is_deleted == False)  # noqa: E712
    return q.all()


def update_folder(db: Session, folder_id: UUID, data: schema.FolderUpdate):
    db_obj = get_folder(db, folder_id)
    if not db_obj:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(db_obj, field, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_folder(db: Session, folder_id: UUID):
    db_obj = get_folder(db, folder_id)
    if not db_obj:
        return None
    if hasattr(db_obj, "is_deleted"):
        db_obj.is_deleted = True
        db.commit()
    else:
        db.delete(db_obj)
        db.commit()
    return db_obj


# ----- LIST CRUD -----


def create_list(db: Session, data: schema.ListCreate):
    new_list = models.List(**data.model_dump())
    db.add(new_list)
    db.commit()
    db.refresh(new_list)
    return new_list


def get_list(db: Session, list_id: UUID):
    q = db.query(models.List).filter_by(id=str(list_id))
    if hasattr(models.List, "is_deleted"):
        q = q.filter(models.List.is_deleted == False)  # noqa: E712
    return q.first()


def get_lists_by_space(db: Session, space_id: str):
    q = db.query(models.List).filter_by(space_id=space_id)
    if hasattr(models.List, "is_deleted"):
        q = q.filter(models.List.is_deleted == False)  # noqa: E712
    return q.all()


def get_lists_by_folder(db: Session, folder_id: str):
    q = db.query(models.List).filter_by(folder_id=folder_id)
    if hasattr(models.List, "is_deleted"):
        q = q.filter(models.List.is_deleted == False)  # noqa: E712
    return q.all()


def update_list(db: Session, list_id: UUID, data: schema.ListUpdate):
    db_obj = get_list(db, list_id)
    if not db_obj:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(db_obj, field, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_list(db: Session, list_id: UUID):
    db_obj = get_list(db, list_id)
    if not db_obj:
        return None
    if hasattr(db_obj, "is_deleted"):
        db_obj.is_deleted = True
        db.commit()
    else:
        db.delete(db_obj)
        db.commit()
    return db_obj
