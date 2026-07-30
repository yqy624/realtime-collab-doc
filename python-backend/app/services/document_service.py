from datetime import datetime

from app.models.user import User
from app.models.document import Document
from app.models.document_snapshot import DocumentSnapshot
from app.models.chat_message import ChatMessage


class DocumentService:
    def __init__(self, db):
        self.db = db

    def create_document(self, title: str | None, content: str | None, is_public: bool | None, user_id: int) -> dict:
        doc = Document(
            title=title or "Untitled Document",
            content=content or "",
            creator_id=user_id,
            is_public=True if is_public is None else is_public,
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
        if data.get("isPublic") is not None:
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
        self.db.delete(doc)
        self.db.commit()

    def get_documents_for_user(self, user_id: int) -> list[dict]:
        merged: dict[int, dict] = {}
        for doc in self.db.query(Document).filter(
                Document.creator_id == user_id).order_by(Document.updated_at.desc()).all():
            merged[doc.id] = self._to_dto(doc)
        for doc in self.db.query(Document).filter(
                Document.is_public == True).order_by(Document.updated_at.desc()).all():
            if doc.id not in merged:
                merged[doc.id] = self._to_dto(doc)
        return list(merged.values())

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

    def find_entity(self, doc_id: int) -> Document:
        doc = self.db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise ValueError("Document not found")
        return doc

    def find_accessible(self, doc_id: int, user_id: int) -> Document:
        doc = self.find_entity(doc_id)
        if doc.creator_id == user_id or doc.is_public:
            return doc
        raise ValueError("No permission to access this document")

    def save(self, doc: Document):
        doc.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def _find_owned(self, doc_id: int, user_id: int) -> Document:
        doc = self.find_entity(doc_id)
        if doc.creator_id != user_id:
            raise ValueError("No permission to operate on this document")
        return doc

    def _find_accessible(self, doc_id: int, user_id: int) -> Document:
        doc = self.find_entity(doc_id)
        if doc.creator_id == user_id or doc.is_public:
            return doc
        raise ValueError("No permission to access this document")

    def _to_dto(self, doc: Document) -> dict:
        return {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "creatorId": doc.creator_id,
            "isPublic": doc.is_public,
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
