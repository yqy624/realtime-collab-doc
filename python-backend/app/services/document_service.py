import secrets
from datetime import datetime

from app.models.user import User
from app.models.document import Document
from app.models.document_share import DocumentShare
from app.models.document_snapshot import DocumentSnapshot
from app.models.chat_message import ChatMessage


class DocumentService:
    def __init__(self, db):
        self.db = db

    # ==================== CRUD ====================

    def create_document(self, title: str | None, content: str | None, is_public: bool | None, user_id: int) -> dict:
        doc = Document(
            title=title or "Untitled Document",
            content=content or "",
            creator_id=user_id,
            is_public=False if is_public is None else is_public,
            share_token=secrets.token_urlsafe(16),
            revision=0,
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return self._to_dto(doc)

    def update_document(self, doc_id: int, data: dict, user_id: int) -> dict:
        doc = self._find_owned(doc_id, user_id)
        if data.get("title") and data["title"].strip():
            doc.title = data["title"]
        if data.get("content") is not None:
            doc.content = data["content"]
        if "isPublic" in data:
            doc.is_public = data["isPublic"]
        if data.get("revision") is not None:
            doc.revision = data["revision"]
        doc.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(doc)
        return self._to_dto(doc)

    def get_document(self, doc_id: int, user_id: int) -> dict:
        doc = self._find_accessible(doc_id, user_id)
        return self._to_dto(doc)

    def delete_document(self, doc_id: int, user_id: int):
        doc = self._find_owned(doc_id, user_id)
        self.db.query(DocumentShare).filter(DocumentShare.document_id == doc_id).delete()
        self.db.delete(doc)
        self.db.commit()

    def get_documents_for_user(self, user_id: int) -> list[dict]:
        merged: dict[int, dict] = {}
        # 1. 我创建的
        for doc in self.db.query(Document).filter(
                Document.creator_id == user_id).order_by(Document.updated_at.desc()).all():
            merged[doc.id] = self._to_dto(doc, viewer_id=user_id)
        # 2. 公开文档
        for doc in self.db.query(Document).filter(
                Document.is_public == True).order_by(Document.updated_at.desc()).all():
            if doc.id not in merged:
                merged[doc.id] = self._to_dto(doc, viewer_id=user_id)
        # 3. 分享给我的
        shares = self.db.query(DocumentShare).filter(DocumentShare.user_id == user_id).all()
        for share in shares:
            doc = self.db.query(Document).filter(Document.id == share.document_id).first()
            if doc and doc.id not in merged:
                merged[doc.id] = self._to_dto(doc, viewer_id=user_id)
        return list(merged.values())

    # ==================== 分享链接 ====================

    def get_or_create_share_link(self, doc_id: int, user_id: int) -> dict:
        """获取或创建分享链接（仅所有者）"""
        doc = self._find_owned(doc_id, user_id)
        if not doc.share_token:
            doc.share_token = secrets.token_urlsafe(16)
            self.db.commit()
            self.db.refresh(doc)
        return self._share_info(doc)

    def set_share_permission(self, doc_id: int, user_id: int, permission: str) -> dict:
        """设置分享链接默认权限 view/edit（仅所有者）"""
        if permission not in ("view", "edit"):
            raise ValueError("权限只能是 view 或 edit")
        doc = self._find_owned(doc_id, user_id)
        doc.share_permission = permission
        self.db.commit()
        self.db.refresh(doc)
        return self._share_info(doc)

    def revoke_share_link(self, doc_id: int, user_id: int) -> dict:
        """关闭分享链接（仅所有者）"""
        doc = self._find_owned(doc_id, user_id)
        doc.share_token = None
        self.db.commit()
        self.db.refresh(doc)
        return self._share_info(doc)

    # ==================== 指定人分享 ====================

    def share_with_user(self, doc_id: int, owner_id: int, username: str, permission: str) -> dict:
        """将文档分享给指定用户（仅所有者）"""
        if permission not in ("view", "edit"):
            raise ValueError("权限只能是 view 或 edit")
        self._find_owned(doc_id, owner_id)
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
        self.db.commit()
        return self._share_info(doc_id, owner_id)

    def unshare_user(self, doc_id: int, owner_id: int, target_user_id: int) -> dict:
        """移除指定用户的访问权限（仅所有者）"""
        self._find_owned(doc_id, owner_id)
        self.db.query(DocumentShare).filter(
            DocumentShare.document_id == doc_id,
            DocumentShare.user_id == target_user_id,
        ).delete()
        self.db.commit()
        return self._share_info(doc_id, owner_id)

    def get_share_info(self, doc_id: int, user_id: int) -> dict:
        """获取分享信息（所有者可查看）"""
        self._find_owned(doc_id, user_id)
        return self._share_info(doc_id, user_id)

    def access_by_token(self, token: str, user_id: int) -> dict:
        """通过分享链接访问文档，返回文档 + 用户权限"""
        doc = self.db.query(Document).filter(Document.share_token == token).first()
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

    def save_snapshot(self, doc_id: int, data: dict | None, user_id: int) -> dict:
        doc = self._find_accessible(doc_id, user_id)
        if data:
            if data.get("title") and data["title"].strip():
                doc.title = data["title"]
            if data.get("content") is not None:
                doc.content = data["content"]
            doc.updated_at = datetime.now()
            self.db.commit()

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
        doc = self._find_owned(snapshot.document_id, user_id)
        doc.title = snapshot.title
        doc.content = snapshot.content
        doc.revision = snapshot.revision
        doc.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(doc)
        return self._to_dto(doc)

    # ==================== 权限判断 ====================

    def find_entity(self, doc_id: int) -> Document:
        doc = self.db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise ValueError("Document not found")
        return doc

    def _get_user_permission(self, doc: Document, user_id: int) -> str | None:
        """返回用户对该文档的权限：owner / edit / view / None"""
        if doc.creator_id == user_id:
            return "owner"
        share = self.db.query(DocumentShare).filter(
            DocumentShare.document_id == doc.id,
            DocumentShare.user_id == user_id,
        ).first()
        if share:
            return share.permission
        if doc.is_public:
            return "view"
        return None

    def find_accessible(self, doc_id: int, user_id: int) -> Document:
        doc = self.find_entity(doc_id)
        if self._get_user_permission(doc, user_id):
            return doc
        raise ValueError("No permission to access this document")

    def _find_owned(self, doc_id: int, user_id: int) -> Document:
        doc = self.find_entity(doc_id)
        if doc.creator_id != user_id:
            raise ValueError("No permission to operate on this document")
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
            "creatorId": doc.creator_id,
            "creatorName": creator.username if creator else "Unknown",
            "isPublic": doc.is_public,
            "shareToken": doc.share_token,
            "sharePermission": doc.share_permission,
            "permission": permission,
            "revision": doc.revision,
            "createdAt": doc.created_at.isoformat() if doc.created_at else None,
            "updatedAt": doc.updated_at.isoformat() if doc.updated_at else None,
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
