from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.schemas.models import ApiResponse
from app.services.platform_service import PlatformService
from app.utils.dependencies import get_current_user_id

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class WorkspaceRequest(BaseModel):
    name: str
    description: str = ""


class WorkspaceMemberRequest(BaseModel):
    username: str
    role: str = "member"


class FolderRequest(BaseModel):
    name: str
    parentId: int | None = None


@router.get("")
def list_workspaces(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(PlatformService(db).list_workspaces(user_id))


@router.post("")
def create_workspace(
    body: WorkspaceRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return ApiResponse.ok(
            PlatformService(db).create_workspace(body.name, body.description, user_id)
        )
    except ValueError as e:
        return ApiResponse.fail(str(e))


@router.put("/{workspace_id}")
def update_workspace(
    workspace_id: int,
    body: WorkspaceRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return ApiResponse.ok(
            PlatformService(db).update_workspace(
                workspace_id,
                user_id,
                body.model_dump(exclude_none=True),
            )
        )
    except ValueError as e:
        return ApiResponse.fail(str(e))


@router.get("/{workspace_id}/members")
def list_members(
    workspace_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return ApiResponse.ok(PlatformService(db).list_members(workspace_id, user_id))
    except ValueError as e:
        return ApiResponse.fail(str(e))


@router.post("/{workspace_id}/members")
def upsert_member(
    workspace_id: int,
    body: WorkspaceMemberRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return ApiResponse.ok(
            PlatformService(db).upsert_member(
                workspace_id,
                user_id,
                body.username,
                body.role,
            )
        )
    except ValueError as e:
        return ApiResponse.fail(str(e))


@router.delete("/{workspace_id}/members/{target_user_id}")
def remove_member(
    workspace_id: int,
    target_user_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        PlatformService(db).remove_member(workspace_id, user_id, target_user_id)
        return ApiResponse.ok(None)
    except ValueError as e:
        return ApiResponse.fail(str(e))


@router.get("/{workspace_id}/folders")
def list_folders(
    workspace_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return ApiResponse.ok(PlatformService(db).list_folders(workspace_id, user_id))
    except ValueError as e:
        return ApiResponse.fail(str(e))


@router.post("/{workspace_id}/folders")
def create_folder(
    workspace_id: int,
    body: FolderRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return ApiResponse.ok(
            PlatformService(db).create_folder(
                workspace_id,
                user_id,
                body.name,
                body.parentId,
            )
        )
    except ValueError as e:
        return ApiResponse.fail(str(e))
