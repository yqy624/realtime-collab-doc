from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.schemas.models import ApiResponse
from app.services.audit_service import AuditService
from app.services.platform_service import PlatformService
from app.utils.dependencies import get_current_user_id

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs")
def list_my_audit_logs(
    limit: int = 100,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(AuditService(db).list_for_actor(user_id, limit))


@router.get("/workspaces/{workspace_id}/logs")
def list_workspace_audit_logs(
    workspace_id: int,
    limit: int = 100,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        PlatformService(db).require_workspace_role(workspace_id, user_id, {"owner", "admin"})
        return ApiResponse.ok(AuditService(db).list_for_workspace(workspace_id, limit))
    except ValueError as e:
        return ApiResponse.fail(str(e))
