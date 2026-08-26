from datetime import datetime

from sqlalchemy import or_

from app.models.document import Document
from app.models.document_permission import DocumentPermission
from app.models.folder import Folder
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.services.audit_service import AuditService


WORKSPACE_ROLES = {"owner", "admin", "member", "viewer"}
DOCUMENT_PERMISSIONS = {"manage", "edit", "comment", "view"}


class PlatformService:
    """Workspace, folder, and direct document permission orchestration."""

    def __init__(self, db):
        self.db = db

    def ensure_personal_workspace(self, user_id: int) -> Workspace:
        workspace = (
            self.db.query(Workspace)
            .filter(Workspace.owner_id == user_id, Workspace.name == "个人空间")
            .first()
        )
        if workspace:
            self._ensure_member(workspace.id, user_id, "owner")
            return workspace

        workspace = Workspace(
            name="个人空间",
            description="默认个人工作空间",
            owner_id=user_id,
        )
        self.db.add(workspace)
        self.db.flush()
        self._ensure_member(workspace.id, user_id, "owner")
        self.db.commit()
        self.db.refresh(workspace)
        return workspace

    def list_workspaces(self, user_id: int) -> list[dict]:
        rows = (
            self.db.query(Workspace, WorkspaceMember)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .filter(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.updated_at.desc(), Workspace.id.desc())
            .all()
        )
        if not rows:
            workspace = self.ensure_personal_workspace(user_id)
            rows = [(workspace, self._get_member(workspace.id, user_id))]
        return [self._workspace_dto(workspace, member.role) for workspace, member in rows]

    def create_workspace(self, name: str, description: str, owner_id: int) -> dict:
        normalized_name = (name or "").strip()
        if not normalized_name:
            raise ValueError("空间名称不能为空")
        workspace = Workspace(
            name=normalized_name[:120],
            description=(description or "").strip(),
            owner_id=owner_id,
        )
        self.db.add(workspace)
        self.db.flush()
        self._ensure_member(workspace.id, owner_id, "owner")
        AuditService(self.db).record(
            owner_id,
            "workspace.create",
            "workspace",
            target_id=workspace.id,
            workspace_id=workspace.id,
            after=self._workspace_audit_state(workspace),
        )
        self.db.commit()
        self.db.refresh(workspace)
        return self._workspace_dto(workspace, "owner")

    def update_workspace(self, workspace_id: int, user_id: int, data: dict) -> dict:
        workspace = self.require_workspace_role(workspace_id, user_id, {"owner", "admin"})
        before = self._workspace_audit_state(workspace)
        if data.get("name") and data["name"].strip():
            workspace.name = data["name"].strip()[:120]
        if data.get("description") is not None:
            workspace.description = str(data["description"]).strip()
        workspace.updated_at = datetime.now()
        AuditService(self.db).record(
            user_id,
            "workspace.update",
            "workspace",
            target_id=workspace.id,
            workspace_id=workspace.id,
            before=before,
            after=self._workspace_audit_state(workspace),
            metadata={"fields": sorted(data.keys())},
        )
        self.db.commit()
        self.db.refresh(workspace)
        role = self.get_workspace_role(workspace.id, user_id) or "viewer"
        return self._workspace_dto(workspace, role)

    def list_members(self, workspace_id: int, user_id: int) -> list[dict]:
        self.require_workspace_access(workspace_id, user_id)
        rows = (
            self.db.query(WorkspaceMember, User)
            .join(User, User.id == WorkspaceMember.user_id)
            .filter(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.created_at.asc(), WorkspaceMember.id.asc())
            .all()
        )
        return [self._member_dto(member, user) for member, user in rows]

    def upsert_member(self, workspace_id: int, actor_id: int, username: str, role: str) -> dict:
        self.require_workspace_role(workspace_id, actor_id, {"owner", "admin"})
        if role not in WORKSPACE_ROLES - {"owner"}:
            raise ValueError("成员角色只能是 admin、member 或 viewer")
        target = self.db.query(User).filter(User.username == username).first()
        if not target:
            raise ValueError("用户不存在")
        workspace = self.require_workspace_access(workspace_id, actor_id)
        if target.id == workspace.owner_id:
            raise ValueError("不能修改空间所有者角色")
        before = self._member_audit_state(self._get_member(workspace_id, target.id))
        member = self._ensure_member(workspace_id, target.id, role)
        AuditService(self.db).record(
            actor_id,
            "workspace.member.upsert",
            "workspace_member",
            target_id=member.id,
            workspace_id=workspace_id,
            before=before,
            after=self._member_audit_state(member),
            metadata={"targetUserId": target.id},
        )
        self.db.commit()
        return self._member_dto(member, target)

    def remove_member(self, workspace_id: int, actor_id: int, target_user_id: int) -> None:
        workspace = self.require_workspace_role(workspace_id, actor_id, {"owner", "admin"})
        if target_user_id == workspace.owner_id:
            raise ValueError("不能移除空间所有者")
        member = self._get_member(workspace_id, target_user_id)
        before = self._member_audit_state(member)
        self.db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == target_user_id,
        ).delete()
        AuditService(self.db).record(
            actor_id,
            "workspace.member.remove",
            "workspace_member",
            target_id=member.id if member else None,
            workspace_id=workspace_id,
            before=before,
            after={},
            metadata={"targetUserId": target_user_id},
        )
        self.db.commit()

    def list_folders(self, workspace_id: int, user_id: int) -> list[dict]:
        self.require_workspace_access(workspace_id, user_id)
        rows = (
            self.db.query(Folder)
            .filter(Folder.workspace_id == workspace_id)
            .order_by(Folder.parent_id.asc(), Folder.sort_order.asc(), Folder.name.asc())
            .all()
        )
        return [self._folder_dto(row) for row in rows]

    def create_folder(
        self,
        workspace_id: int,
        user_id: int,
        name: str,
        parent_id: int | None = None,
    ) -> dict:
        self.require_workspace_role(workspace_id, user_id, {"owner", "admin", "member"})
        normalized_name = (name or "").strip()
        if not normalized_name:
            raise ValueError("文件夹名称不能为空")
        if parent_id is not None:
            parent = self.db.query(Folder).filter(Folder.id == parent_id).first()
            if not parent or parent.workspace_id != workspace_id:
                raise ValueError("父文件夹不存在")
        folder = Folder(
            workspace_id=workspace_id,
            parent_id=parent_id,
            name=normalized_name[:120],
            creator_id=user_id,
        )
        self.db.add(folder)
        self.db.flush()
        AuditService(self.db).record(
            user_id,
            "folder.create",
            "folder",
            target_id=folder.id,
            workspace_id=workspace_id,
            after={
                "id": folder.id,
                "name": folder.name,
                "workspaceId": folder.workspace_id,
                "parentId": folder.parent_id,
            },
        )
        self.db.commit()
        self.db.refresh(folder)
        return self._folder_dto(folder)

    def get_workspace_role(self, workspace_id: int, user_id: int) -> str | None:
        member = self._get_member(workspace_id, user_id)
        return member.role if member else None

    def require_workspace_access(self, workspace_id: int, user_id: int) -> Workspace:
        workspace = self.db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            raise ValueError("空间不存在")
        if workspace.owner_id == user_id:
            self._ensure_member(workspace.id, user_id, "owner")
            return workspace
        if self._get_member(workspace.id, user_id):
            return workspace
        raise ValueError("No permission to access this workspace")

    def require_workspace_role(self, workspace_id: int, user_id: int, roles: set[str]) -> Workspace:
        workspace = self.require_workspace_access(workspace_id, user_id)
        role = self.get_workspace_role(workspace_id, user_id)
        if role not in roles:
            raise ValueError("No permission to operate on this workspace")
        return workspace

    def list_document_permissions(self, document_id: int, user_id: int) -> list[dict]:
        document = self._find_document(document_id)
        if self.document_permission(document, user_id) not in ("owner", "manage"):
            raise ValueError("No permission to manage this document")
        rows = (
            self.db.query(DocumentPermission, User)
            .join(User, User.id == DocumentPermission.user_id)
            .filter(DocumentPermission.document_id == document_id)
            .order_by(DocumentPermission.updated_at.desc(), DocumentPermission.id.desc())
            .all()
        )
        return [self._document_permission_dto(permission, user) for permission, user in rows]

    def upsert_document_permission(
        self,
        document_id: int,
        actor_id: int,
        username: str,
        permission: str,
    ) -> dict:
        document = self._find_document(document_id)
        if self.document_permission(document, actor_id) not in ("owner", "manage"):
            raise ValueError("No permission to manage this document")
        if permission not in DOCUMENT_PERMISSIONS:
            raise ValueError("文档权限只能是 manage、edit、comment 或 view")
        target = self.db.query(User).filter(User.username == username).first()
        if not target:
            raise ValueError("用户不存在")
        if target.id == document.creator_id:
            raise ValueError("不能修改文档创建者权限")
        row = (
            self.db.query(DocumentPermission)
            .filter(
                DocumentPermission.document_id == document_id,
                DocumentPermission.user_id == target.id,
            )
            .first()
        )
        before = self._document_permission_audit_state(row)
        if row:
            row.permission = permission
            row.source = "manual"
            row.updated_at = datetime.now()
        else:
            row = DocumentPermission(
                document_id=document_id,
                user_id=target.id,
                permission=permission,
                source="manual",
            )
            self.db.add(row)
            self.db.flush()
        AuditService(self.db).record(
            actor_id,
            "document.permission.upsert",
            "document_permission",
            target_id=row.id,
            workspace_id=document.workspace_id,
            document_id=document.id,
            before=before,
            after=self._document_permission_audit_state(row),
            metadata={"targetUserId": target.id},
        )
        self.db.commit()
        self.db.refresh(row)
        return self._document_permission_dto(row, target)

    def remove_document_permission(self, document_id: int, actor_id: int, target_user_id: int) -> None:
        document = self._find_document(document_id)
        if self.document_permission(document, actor_id) not in ("owner", "manage"):
            raise ValueError("No permission to manage this document")
        if target_user_id == document.creator_id:
            raise ValueError("不能移除文档创建者权限")
        row = (
            self.db.query(DocumentPermission)
            .filter(
                DocumentPermission.document_id == document_id,
                DocumentPermission.user_id == target_user_id,
            )
            .first()
        )
        before = self._document_permission_audit_state(row)
        self.db.query(DocumentPermission).filter(
            DocumentPermission.document_id == document_id,
            DocumentPermission.user_id == target_user_id,
        ).delete()
        AuditService(self.db).record(
            actor_id,
            "document.permission.remove",
            "document_permission",
            target_id=row.id if row else None,
            workspace_id=document.workspace_id,
            document_id=document.id,
            before=before,
            after={},
            metadata={"targetUserId": target_user_id},
        )
        self.db.commit()

    def document_permission(self, document: Document, user_id: int) -> str | None:
        if document.creator_id == user_id:
            return "owner"
        direct = (
            self.db.query(DocumentPermission)
            .filter(
                DocumentPermission.document_id == document.id,
                DocumentPermission.user_id == user_id,
            )
            .first()
        )
        if direct:
            return direct.permission
        if document.workspace_id:
            role = self.get_workspace_role(document.workspace_id, user_id)
            if role in ("owner", "admin"):
                return "manage"
            if role == "member":
                return "edit"
            if role == "viewer":
                return "view"
        return None

    def visible_document_filter(self, user_id: int):
        workspace_ids = [
            row.workspace_id
            for row in self.db.query(WorkspaceMember.workspace_id)
            .filter(WorkspaceMember.user_id == user_id)
            .all()
        ]
        direct_document_ids = [
            row.document_id
            for row in self.db.query(DocumentPermission.document_id)
            .filter(DocumentPermission.user_id == user_id)
            .all()
        ]
        return or_(
            Document.creator_id == user_id,
            Document.is_public.is_(True),
            Document.workspace_id.in_(workspace_ids or [-1]),
            Document.id.in_(direct_document_ids or [-1]),
        )

    def _ensure_member(self, workspace_id: int, user_id: int, role: str) -> WorkspaceMember:
        member = self._get_member(workspace_id, user_id)
        if member:
            if member.role != role and member.role != "owner":
                member.role = role
                member.updated_at = datetime.now()
            return member
        member = WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role=role)
        self.db.add(member)
        self.db.flush()
        return member

    def _get_member(self, workspace_id: int, user_id: int) -> WorkspaceMember | None:
        return (
            self.db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
            .first()
        )

    def _find_document(self, document_id: int) -> Document:
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError("Document not found")
        return document

    def _workspace_dto(self, workspace: Workspace, role: str) -> dict:
        doc_count = (
            self.db.query(Document)
            .filter(Document.workspace_id == workspace.id, Document.deleted_at.is_(None))
            .count()
        )
        member_count = (
            self.db.query(WorkspaceMember)
            .filter(WorkspaceMember.workspace_id == workspace.id)
            .count()
        )
        return {
            "id": workspace.id,
            "name": workspace.name,
            "description": workspace.description,
            "ownerId": workspace.owner_id,
            "role": role,
            "documentCount": doc_count,
            "memberCount": member_count,
            "createdAt": workspace.created_at.isoformat() if workspace.created_at else None,
            "updatedAt": workspace.updated_at.isoformat() if workspace.updated_at else None,
        }

    @staticmethod
    def _member_dto(member: WorkspaceMember, user: User) -> dict:
        return {
            "id": member.id,
            "workspaceId": member.workspace_id,
            "userId": member.user_id,
            "username": user.username,
            "avatarUrl": user.avatar_url or "",
            "role": member.role,
            "createdAt": member.created_at.isoformat() if member.created_at else None,
            "updatedAt": member.updated_at.isoformat() if member.updated_at else None,
        }

    @staticmethod
    def _folder_dto(folder: Folder) -> dict:
        return {
            "id": folder.id,
            "workspaceId": folder.workspace_id,
            "parentId": folder.parent_id,
            "name": folder.name,
            "creatorId": folder.creator_id,
            "sortOrder": folder.sort_order,
            "createdAt": folder.created_at.isoformat() if folder.created_at else None,
            "updatedAt": folder.updated_at.isoformat() if folder.updated_at else None,
        }

    @staticmethod
    def _document_permission_dto(permission: DocumentPermission, user: User) -> dict:
        return {
            "id": permission.id,
            "documentId": permission.document_id,
            "userId": permission.user_id,
            "username": user.username,
            "avatarUrl": user.avatar_url or "",
            "permission": permission.permission,
            "source": permission.source,
            "createdAt": permission.created_at.isoformat() if permission.created_at else None,
            "updatedAt": permission.updated_at.isoformat() if permission.updated_at else None,
        }

    @staticmethod
    def _workspace_audit_state(workspace: Workspace) -> dict:
        return {
            "id": workspace.id,
            "name": workspace.name,
            "description": workspace.description,
            "ownerId": workspace.owner_id,
        }

    @staticmethod
    def _member_audit_state(member: WorkspaceMember | None) -> dict:
        if not member:
            return {}
        return {
            "id": member.id,
            "workspaceId": member.workspace_id,
            "userId": member.user_id,
            "role": member.role,
        }

    @staticmethod
    def _document_permission_audit_state(permission: DocumentPermission | None) -> dict:
        if not permission:
            return {}
        return {
            "id": permission.id,
            "documentId": permission.document_id,
            "userId": permission.user_id,
            "permission": permission.permission,
            "source": permission.source,
        }
