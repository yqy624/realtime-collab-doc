import secrets
from datetime import datetime

from app.models.user import User
from app.models.document import Document
from app.models.document_permission import DocumentPermission
from app.models.document_share import DocumentShare
from app.models.document_snapshot import DocumentSnapshot
from app.models.chat_message import ChatMessage
from app.models.folder import Folder
from app.services.audit_service import AuditService
from app.services.rag_service import RAGService
from app.services.platform_service import PlatformService


class DocumentService:
    def __init__(self, db):
        self.db = db

    # ==================== CRUD ====================

    def create_document(
        self,
        title: str | None,
        content: str | None,
        is_public: bool | None,
        user_id: int,
        workspace_id: int | None = None,
        folder_id: int | None = None,
        content_format: str | None = None,
    ) -> dict:
        if workspace_id is None and folder_id is None:
            workspace_id = PlatformService(self.db).ensure_personal_workspace(user_id).id
        workspace_id, folder_id = self._validate_location(workspace_id, folder_id, user_id)
        doc = Document(
            title=title or "Untitled Document",
            content=content or "",
            content_format=content_format or "plain_text",
            creator_id=user_id,
            workspace_id=workspace_id,
            folder_id=folder_id,
            is_public=False if is_public is None else is_public,
            share_token=secrets.token_urlsafe(16),
            revision=0,
        )
        self.db.add(doc)
        self.db.flush()
        AuditService(self.db).record(
            user_id,
            "document.create",
            "document",
            target_id=doc.id,
            workspace_id=workspace_id,
            document_id=doc.id,
            before={},
            after={
                "title": doc.title,
                "workspaceId": workspace_id,
                "folderId": folder_id,
                "isPublic": doc.is_public,
            },
        )
        self.db.commit()
        self.db.refresh(doc)
        RAGService(self.db).ensure_document_index(doc)
        return self._to_dto(doc)

    def update_document(self, doc_id: int, data: dict, user_id: int) -> dict:
        doc = self._find_manageable(doc_id, user_id)
        before = self._audit_document_state(doc)
        if data.get("title") and data["title"].strip():
            doc.title = data["title"]
        if data.get("content") is not None:
            doc.content = data["content"]
        if data.get("contentFormat"):
            doc.content_format = data["contentFormat"]
        if "workspaceId" in data or "folderId" in data:
            doc.workspace_id, doc.folder_id = self._validate_location(
                data.get("workspaceId", doc.workspace_id),
                data.get("folderId", doc.folder_id),
                user_id,
            )
        if "isPublic" in data:
            doc.is_public = data["isPublic"]
        if data.get("revision") is not None:
            doc.revision = data["revision"]
        doc.updated_at = datetime.now()
        AuditService(self.db).record(
            user_id,
            "document.update",
            "document",
            target_id=doc.id,
            workspace_id=doc.workspace_id,
            document_id=doc.id,
            before=before,
            after=self._audit_document_state(doc),
            metadata={"fields": sorted(data.keys())},
        )
        self.db.commit()
        self.db.refresh(doc)
        RAGService(self.db).ensure_document_index(doc)
        return self._to_dto(doc)

    def get_document(self, doc_id: int, user_id: int) -> dict:
        doc = self._find_accessible(doc_id, user_id)
        return self._to_dto(doc, viewer_id=user_id)

    def delete_document(self, doc_id: int, user_id: int, reason: str = "user_deleted"):
        doc = self._find_manageable(doc_id, user_id)
        before = self._audit_document_state(doc)
        doc.deleted_at = datetime.now()
        doc.deleted_by = user_id
        doc.delete_reason = (reason or "user_deleted")[:240]
        doc.updated_at = datetime.now()
        AuditService(self.db).record(
            user_id,
            "document.soft_delete",
            "document",
            target_id=doc.id,
            workspace_id=doc.workspace_id,
            document_id=doc.id,
            before=before,
            after=self._audit_document_state(doc),
        )
        self.db.commit()

    def restore_deleted_document(self, doc_id: int, user_id: int) -> dict:
        doc = self._find_manageable(doc_id, user_id, include_deleted=True)
        if doc.deleted_at is None:
            return self._to_dto(doc, viewer_id=user_id)
        before = self._audit_document_state(doc)
        doc.deleted_at = None
        doc.deleted_by = None
        doc.delete_reason = ""
        doc.updated_at = datetime.now()
        AuditService(self.db).record(
            user_id,
            "document.restore",
            "document",
            target_id=doc.id,
            workspace_id=doc.workspace_id,
            document_id=doc.id,
            before=before,
            after=self._audit_document_state(doc),
        )
        self.db.commit()
        self.db.refresh(doc)
        RAGService(self.db).ensure_document_index(doc)
        return self._to_dto(doc, viewer_id=user_id)

    def hard_delete_document(self, doc_id: int, user_id: int) -> None:
        doc = self._find_manageable(doc_id, user_id, include_deleted=True)
        if doc.deleted_at is None:
            raise ValueError("Document must be moved to trash before permanent deletion")
        before = self._audit_document_state(doc)
        self.db.query(DocumentShare).filter(DocumentShare.document_id == doc_id).delete()
        self.db.query(DocumentPermission).filter(DocumentPermission.document_id == doc_id).delete()
        from app.models.document_chunk import DocumentChunk
        from app.models.embedding_job import EmbeddingJob
        from app.models.knowledge_chunk import KnowledgeChunk
        from app.models.knowledge_source import KnowledgeSource
        source_ids = [
            row.id
            for row in self.db.query(KnowledgeSource.id)
            .filter(KnowledgeSource.document_id == doc_id)
            .all()
        ]
        if source_ids:
            self.db.query(KnowledgeChunk).filter(KnowledgeChunk.source_id.in_(source_ids)).delete()
            self.db.query(EmbeddingJob).filter(EmbeddingJob.source_id.in_(source_ids)).delete()
            self.db.query(KnowledgeSource).filter(KnowledgeSource.id.in_(source_ids)).delete()
        self.db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).delete()
        self.db.delete(doc)
        AuditService(self.db).record(
            user_id,
            "document.hard_delete",
            "document",
            target_id=doc_id,
            workspace_id=before.get("workspaceId"),
            document_id=doc_id,
            before=before,
            after={},
        )
        self.db.commit()

    def get_deleted_documents_for_user(self, user_id: int) -> list[dict]:
        platform = PlatformService(self.db)
        rows = (
            self.db.query(Document)
            .filter(Document.deleted_at.is_not(None))
            .filter(platform.visible_document_filter(user_id))
            .order_by(Document.deleted_at.desc(), Document.id.desc())
            .limit(100)
            .all()
        )
        manageable = [
            row for row in rows
            if self._get_user_permission(row, user_id) in ("owner", "manage")
        ]
        return [self._to_dto(row, viewer_id=user_id) for row in manageable]

    def get_documents_for_user(
        self,
        user_id: int,
        workspace_id: int | None = None,
        folder_id: int | None = None,
    ) -> list[dict]:
        merged: dict[int, dict] = {}
        platform = PlatformService(self.db)
        base_query = self.db.query(Document)
        base_query = base_query.filter(Document.deleted_at.is_(None))
        if workspace_id is not None:
            platform.require_workspace_access(workspace_id, user_id)
            base_query = base_query.filter(Document.workspace_id == workspace_id)
        if folder_id is not None:
            base_query = base_query.filter(Document.folder_id == folder_id)

        # 1. 我创建的
        for doc in base_query.filter(
                Document.creator_id == user_id).order_by(Document.updated_at.desc()).all():
            merged[doc.id] = self._to_dto(doc, viewer_id=user_id)
        # 2. 公开文档
        for doc in base_query.filter(
                Document.is_public == True).order_by(Document.updated_at.desc()).all():
            if doc.id not in merged:
                merged[doc.id] = self._to_dto(doc, viewer_id=user_id)
        # 3. 分享给我的
        shares = self.db.query(DocumentShare).filter(DocumentShare.user_id == user_id).all()
        for share in shares:
            doc = self.db.query(Document).filter(
                Document.id == share.document_id,
                Document.deleted_at.is_(None),
            ).first()
            if doc and doc.id not in merged:
                if workspace_id is not None and doc.workspace_id != workspace_id:
                    continue
                if folder_id is not None and doc.folder_id != folder_id:
                    continue
                merged[doc.id] = self._to_dto(doc, viewer_id=user_id)
        # 4. 空间成员与文档级授权
        for doc in base_query.filter(platform.visible_document_filter(user_id)).order_by(Document.updated_at.desc()).all():
            if doc.id not in merged:
                merged[doc.id] = self._to_dto(doc, viewer_id=user_id)
        return list(merged.values())

    # ==================== 分享链接 ====================

    def get_or_create_share_link(self, doc_id: int, user_id: int) -> dict:
        """获取或创建分享链接（仅所有者）"""
        doc = self._find_manageable(doc_id, user_id)
        before = self._audit_document_state(doc)
        if not doc.share_token:
            doc.share_token = secrets.token_urlsafe(16)
            AuditService(self.db).record(
                user_id,
                "document.share_link.create",
                "document",
                target_id=doc.id,
                workspace_id=doc.workspace_id,
                document_id=doc.id,
                before=before,
                after=self._audit_document_state(doc),
            )
            self.db.commit()
            self.db.refresh(doc)
        return self._share_info(doc)

    def set_share_permission(self, doc_id: int, user_id: int, permission: str) -> dict:
        """设置分享链接默认权限 view/edit（仅所有者）"""
        if permission not in ("view", "edit"):
            raise ValueError("权限只能是 view 或 edit")
        doc = self._find_manageable(doc_id, user_id)
        before = self._audit_document_state(doc)
        doc.share_permission = permission
        AuditService(self.db).record(
            user_id,
            "document.share_link.update",
            "document",
            target_id=doc.id,
            workspace_id=doc.workspace_id,
            document_id=doc.id,
            before=before,
            after=self._audit_document_state(doc),
        )
        self.db.commit()
        self.db.refresh(doc)
        return self._share_info(doc)

    def revoke_share_link(self, doc_id: int, user_id: int) -> dict:
        """关闭分享链接（仅所有者）"""
        doc = self._find_manageable(doc_id, user_id)
        before = self._audit_document_state(doc)
        doc.share_token = None
        AuditService(self.db).record(
            user_id,
            "document.share_link.revoke",
            "document",
            target_id=doc.id,
            workspace_id=doc.workspace_id,
            document_id=doc.id,
            before=before,
            after=self._audit_document_state(doc),
        )
        self.db.commit()
        self.db.refresh(doc)
        return self._share_info(doc)

    # ==================== 指定人分享 ====================

    def share_with_user(self, doc_id: int, owner_id: int, username: str, permission: str) -> dict:
        """将文档分享给指定用户（仅所有者）"""
        if permission not in ("view", "edit"):
            raise ValueError("权限只能是 view 或 edit")
        self._find_manageable(doc_id, owner_id)
        target = self.db.query(User).filter(User.username == username).first()
        if not target:
            raise ValueError("用户不存在")
        if target.id == owner_id:
            raise ValueError("不能分享给自己")
        existing = self.db.query(DocumentShare).filter(
            DocumentShare.document_id == doc_id,
            DocumentShare.user_id == target.id,
        ).first()
        if existing:
            existing.permission = permission
        else:
            self.db.add(DocumentShare(
                document_id=doc_id,
                user_id=target.id,
                permission=permission,
            ))
        doc = self.find_entity(doc_id)
        AuditService(self.db).record(
            owner_id,
            "document.share_user.upsert",
            "document",
            target_id=doc_id,
            workspace_id=doc.workspace_id,
            document_id=doc_id,
            metadata={"targetUserId": target.id, "permission": permission},
        )
        self.db.commit()
        return self._share_info(doc_id, owner_id)

    def unshare_user(self, doc_id: int, owner_id: int, target_user_id: int) -> dict:
        """移除指定用户的访问权限（仅所有者）"""
        self._find_manageable(doc_id, owner_id)
        self.db.query(DocumentShare).filter(
            DocumentShare.document_id == doc_id,
            DocumentShare.user_id == target_user_id,
        ).delete()
        doc = self.find_entity(doc_id)
        AuditService(self.db).record(
            owner_id,
            "document.share_user.remove",
            "document",
            target_id=doc_id,
            workspace_id=doc.workspace_id,
            document_id=doc_id,
            metadata={"targetUserId": target_user_id},
        )
        self.db.commit()
        return self._share_info(doc_id, owner_id)

    def get_share_info(self, doc_id: int, user_id: int) -> dict:
        """获取分享信息（所有者可查看）"""
        self._find_manageable(doc_id, user_id)
        return self._share_info(doc_id, user_id)

    def access_by_token(self, token: str, user_id: int) -> dict:
        """通过分享链接访问文档，返回文档 + 用户权限"""
        doc = self.db.query(Document).filter(
            Document.share_token == token,
            Document.deleted_at.is_(None),
        ).first()
        if not doc:
            raise ValueError("分享链接无效或已失效")
        # 所有者直接放行
        if doc.creator_id == user_id:
            return self._to_dto(doc, viewer_id=user_id)
        # 链接访问者：按链接权限（view/edit），已指定分享的取更高权限
        dto = self._to_dto(doc, viewer_id=user_id)
        perm = self._get_user_permission(doc, user_id)  # None | view | edit
        link_perm = doc.share_permission  # view | edit
        if perm == "edit" or link_perm == "edit":
            dto["permission"] = "edit"
        else:
            dto["permission"] = "view"
        return dto

    # ==================== 快照 ====================

    def persist_document(self, doc_id: int, data: dict | None, user_id: int) -> dict:
        doc = self._find_editable(doc_id, user_id)
        content_updated = False
        if data and data.get("content") is not None and data["content"] != doc.content:
            doc.content = data["content"]
            content_updated = True
        doc.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(doc)
        if content_updated:
            try:
                RAGService(self.db).ensure_document_index(doc)
            except Exception:
                self.db.rollback()
        return self._to_dto(doc, viewer_id=user_id)

    def save_snapshot(self, doc_id: int, data: dict | None, user_id: int) -> dict:
        # Saving a snapshot may mutate the document and must be write-authorized.
        doc = self._find_editable(doc_id, user_id)
        if data:
            if data.get("title") and data["title"].strip():
                doc.title = data["title"]
            if data.get("content") is not None:
                doc.content = data["content"]
            doc.updated_at = datetime.now()
            self.db.commit()
            RAGService(self.db).ensure_document_index(doc)

        snapshot = DocumentSnapshot(
            document_id=doc.id,
            title=doc.title,
            content=doc.content,
            revision=doc.revision,
            user_id=user_id,
        )
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        return self._to_snapshot_dto(snapshot)

    def get_snapshots(self, doc_id: int, user_id: int) -> list[dict]:
        self._find_accessible(doc_id, user_id)
        snapshots = self.db.query(DocumentSnapshot).filter(
            DocumentSnapshot.document_id == doc_id).order_by(DocumentSnapshot.created_at.desc()).all()
        return [self._to_snapshot_dto(s) for s in snapshots]

    def restore_snapshot(self, snapshot_id: int, doc_id: int, user_id: int) -> dict:
        snapshot = self.db.query(DocumentSnapshot).filter(DocumentSnapshot.id == snapshot_id).first()
        if not snapshot:
            raise ValueError("Snapshot not found")
        if snapshot.document_id != doc_id:
            raise ValueError("Snapshot does not belong to this document")
        doc = self._find_owned(doc_id, user_id)
        doc.title = snapshot.title
        doc.content = snapshot.content
        doc.revision = snapshot.revision
        doc.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(doc)
        RAGService(self.db).ensure_document_index(doc)
        return self._to_dto(doc, viewer_id=user_id)

    # ==================== 权限判断 ====================

    def find_entity(self, doc_id: int, include_deleted: bool = False) -> Document:
        doc = self.db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise ValueError("Document not found")
        if doc.deleted_at is not None and not include_deleted:
            raise ValueError("Document has been deleted")
        return doc

    def _get_user_permission(self, doc: Document, user_id: int) -> str | None:
        """返回用户对该文档的权限：owner / manage / edit / comment / view / None"""
        if doc.creator_id == user_id:
            return "owner"
        permission_rank = {
            "view": 1,
            "comment": 2,
            "edit": 3,
            "manage": 4,
            "owner": 5,
        }
        permissions = []
        platform_permission = PlatformService(self.db).document_permission(doc, user_id)
        if platform_permission:
            permissions.append(platform_permission)
        share = self.db.query(DocumentShare).filter(
            DocumentShare.document_id == doc.id,
            DocumentShare.user_id == user_id,
        ).first()
        if share:
            permissions.append(share.permission)
        if doc.is_public:
            permissions.append("view")
        return max(
            permissions,
            key=lambda permission: permission_rank.get(permission, 0),
            default=None,
        )

    def find_accessible(self, doc_id: int, user_id: int) -> Document:
        doc = self.find_entity(doc_id)
        if self._get_user_permission(doc, user_id):
            return doc
        raise ValueError("No permission to access this document")

    def _find_owned(self, doc_id: int, user_id: int, include_deleted: bool = False) -> Document:
        doc = self.find_entity(doc_id, include_deleted=include_deleted)
        if doc.creator_id != user_id:
            raise ValueError("No permission to operate on this document")
        return doc

    def _find_manageable(self, doc_id: int, user_id: int, include_deleted: bool = False) -> Document:
        doc = self.find_entity(doc_id, include_deleted=include_deleted)
        if self._get_user_permission(doc, user_id) in ("owner", "manage"):
            return doc
        raise ValueError("No permission to operate on this document")

    def _find_editable(self, doc_id: int, user_id: int) -> Document:
        doc = self.find_entity(doc_id)
        permission = self._get_user_permission(doc, user_id)
        if permission not in ("owner", "manage", "edit"):
            raise ValueError("No permission to edit this document")
        return doc

    def _find_accessible(self, doc_id: int, user_id: int) -> Document:
        doc = self.find_entity(doc_id)
        if self._get_user_permission(doc, user_id):
            return doc
        raise ValueError("No permission to access this document")

    def save(self, doc: Document):
        doc.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def _validate_location(
        self,
        workspace_id: int | None,
        folder_id: int | None,
        user_id: int,
    ) -> tuple[int | None, int | None]:
        platform = PlatformService(self.db)
        if workspace_id is not None:
            platform.require_workspace_role(workspace_id, user_id, {"owner", "admin", "member"})
        if folder_id is not None:
            folder = self.db.query(Folder).filter(Folder.id == folder_id).first()
            if not folder:
                raise ValueError("文件夹不存在")
            if workspace_id is None:
                workspace_id = folder.workspace_id
            if folder.workspace_id != workspace_id:
                raise ValueError("文件夹不属于当前空间")
            platform.require_workspace_role(folder.workspace_id, user_id, {"owner", "admin", "member"})
        return workspace_id, folder_id

    # ==================== DTO ====================

    def _share_info(self, doc: Document | int, owner_id: int | None = None) -> dict:
        if isinstance(doc, int):
            doc = self.find_entity(doc)
        shares = self.db.query(DocumentShare).filter(
            DocumentShare.document_id == doc.id).all()
        users = []
        for s in shares:
            u = self.db.query(User).filter(User.id == s.user_id).first()
            users.append({
                "id": s.user_id,
                "username": u.username if u else "Unknown",
                "avatarUrl": u.avatar_url if u else "",
                "permission": s.permission,
            })
        share_url = f"{doc.share_token}" if doc.share_token else None
        return {
            "shareToken": doc.share_token,
            "sharePermission": doc.share_permission,
            "shareUrl": share_url,
            "isPublic": doc.is_public,
            "users": users,
        }

    def _to_dto(self, doc: Document, viewer_id: int | None = None) -> dict:
        creator = self.db.query(User).filter(User.id == doc.creator_id).first()
        permission = self._get_user_permission(doc, viewer_id) if viewer_id else "owner"
        return {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "contentFormat": doc.content_format,
            "creatorId": doc.creator_id,
            "creatorName": creator.username if creator else "Unknown",
            "workspaceId": doc.workspace_id,
            "folderId": doc.folder_id,
            "isPublic": doc.is_public,
            "shareToken": doc.share_token,
            "sharePermission": doc.share_permission,
            "permission": permission,
            "revision": doc.revision,
            "createdAt": doc.created_at.isoformat() if doc.created_at else None,
            "updatedAt": doc.updated_at.isoformat() if doc.updated_at else None,
            "deletedAt": doc.deleted_at.isoformat() if doc.deleted_at else None,
            "deletedBy": doc.deleted_by,
            "deleteReason": doc.delete_reason,
        }

    def _to_snapshot_dto(self, snap: DocumentSnapshot) -> dict:
        user = self.db.query(User).filter(User.id == snap.user_id).first()
        return {
            "id": snap.id,
            "documentId": snap.document_id,
            "title": snap.title,
            "content": snap.content,
            "revision": snap.revision,
            "userId": snap.user_id,
            "userName": user.username if user else "Unknown",
            "createdAt": snap.created_at.isoformat() if snap.created_at else None,
        }

    @staticmethod
    def _audit_document_state(doc: Document) -> dict:
        return {
            "id": doc.id,
            "title": doc.title,
            "workspaceId": doc.workspace_id,
            "folderId": doc.folder_id,
            "isPublic": doc.is_public,
            "shareToken": doc.share_token,
            "sharePermission": doc.share_permission,
            "revision": doc.revision,
            "deletedAt": doc.deleted_at.isoformat() if doc.deleted_at else None,
            "deletedBy": doc.deleted_by,
            "deleteReason": doc.delete_reason,
        }
