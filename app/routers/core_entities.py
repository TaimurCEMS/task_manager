# File: /app/routers/core_entities.py | Version: 1.6 | Path: /app/routers/core_entities.py
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.permissions import Role, get_workspace_role, require_role
from app.crud import core_entities as crud_core
from app.db.session import get_db
from app.routers.auth_dependencies import get_me  # Authenticated user from token
from app.schemas import core_entities as schema

router = APIRouter(tags=["Core Entities"])

# ----- WORKSPACE ROUTES -----


@router.post("/workspaces/", response_model=schema.WorkspaceOut)
def create_workspace(
    data: schema.WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    # Any authenticated user may create a workspace; they will be Owner in that workspace.
    return crud_core.create_workspace(db, data, owner_id=str(current_user.id))


@router.get("/workspaces/", response_model=List[schema.WorkspaceOut])
def get_my_workspaces(
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    # Return by membership (Owner/Admin/Member/Guest), not just ownership
    return crud_core.get_workspaces_for_user(db, user_id=str(current_user.id))


@router.get("/workspaces/{workspace_id}", response_model=schema.WorkspaceOut)
def get_workspace(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    # Must be a member of the workspace to view
    role = get_workspace_role(
        db, user_id=str(current_user.id), workspace_id=str(workspace_id)
    )
    if role is None:
        raise HTTPException(status_code=403, detail="No access to this workspace")
    workspace = crud_core.get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


# ----- SPACE ROUTES -----


@router.post("/spaces/", response_model=schema.SpaceOut)
def create_space(
    data: schema.SpaceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    # Require Member+ in the target workspace
    require_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(data.workspace_id),
        minimum=Role.MEMBER,
    )
    return crud_core.create_space(db, data)


@router.get("/spaces/by-workspace/{workspace_id}", response_model=List[schema.SpaceOut])
def get_spaces(
    workspace_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    role = get_workspace_role(
        db, user_id=str(current_user.id), workspace_id=str(workspace_id)
    )
    if role is None:
        raise HTTPException(status_code=403, detail="No access to this workspace")
    return crud_core.get_spaces_by_workspace(db, str(workspace_id))


# ----- FOLDER ROUTES -----


@router.post("/folders/", response_model=schema.FolderOut)
def create_folder(
    data: schema.FolderCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    # Validate membership via the parent space's workspace
    space = crud_core.get_space(db, data.space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    require_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(space.workspace_id),
        minimum=Role.MEMBER,
    )
    return crud_core.create_folder(db, data)


@router.get("/folders/by-space/{space_id}", response_model=List[schema.FolderOut])
def get_folders(
    space_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    space = crud_core.get_space(db, space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    role = get_workspace_role(
        db, user_id=str(current_user.id), workspace_id=str(space.workspace_id)
    )
    if role is None:
        raise HTTPException(status_code=403, detail="No access to this space")
    return crud_core.get_folders_by_space(db, str(space_id))


# ----- LIST ROUTES -----


@router.post("/lists/", response_model=schema.ListOut)
def create_list(
    data: schema.ListCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    # Validate membership via the parent space/folder → workspace
    space = crud_core.get_space(db, data.space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    require_role(
        db,
        user_id=str(current_user.id),
        workspace_id=str(space.workspace_id),
        minimum=Role.MEMBER,
    )
    return crud_core.create_list(db, data)


@router.get("/lists/by-space/{space_id}", response_model=List[schema.ListOut])
def get_lists_by_space(
    space_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    space = crud_core.get_space(db, space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    role = get_workspace_role(
        db, user_id=str(current_user.id), workspace_id=str(space.workspace_id)
    )
    if role is None:
        raise HTTPException(status_code=403, detail="No access to this space")
    return crud_core.get_lists_by_space(db, str(space_id))


@router.get("/lists/by-folder/{folder_id}", response_model=List[schema.ListOut])
def get_lists_by_folder(
    folder_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_me),
):
    folder = crud_core.get_folder(db, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    # Get space -> workspace for membership
    space = crud_core.get_space(db, folder.space_id)
    role = get_workspace_role(
        db, user_id=str(current_user.id), workspace_id=str(space.workspace_id)
    )
    if role is None:
        raise HTTPException(status_code=403, detail="No access to this folder")
    return crud_core.get_lists_by_folder(db, str(folder_id))
