from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage
from app.models.database import get_db
from app.models.user import User
from app.schemas.models import ApiResponse, DocumentDTO
from app.services.document_service import DocumentService
from app.utils.dependencies import get_current_user_id

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("")
def list_documents(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    docs = DocumentService(db).get_documents_for_user(user_id)
    return ApiResponse.ok(docs)


@router.post("")
def create_document(body: DocumentDTO, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    result = DocumentService(db).create_document(body.title, body.content, body.isPublic, user_id)
    return ApiResponse.ok(result)


@router.get("/{doc_id}")
def get_document(doc_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    try:
        result = DocumentService(db).get_document(doc_id, user_id)
        return ApiResponse.ok(result)
    except ValueError as e:
        return ApiResponse.fail(str(e))


@router.put("/{doc_id}")
def update_document(doc_id: int, body: DocumentDTO, user_id: int = Depends(get_current_user_id),
                    db: Session = Depends(get_db)):
    try:
        data = {k: v for k, v in body.model_dump(exclude_none=True).items()}
        result = DocumentService(db).update_document(doc_id, data, user_id)
        return ApiResponse.ok(result)
    except ValueError as e:
        return ApiResponse.fail(str(e))


@router.delete("/{doc_id}")
def delete_document(doc_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    try:
        DocumentService(db).delete_document(doc_id, user_id)
        return ApiResponse.ok(None)
    except ValueError as e:
        return ApiResponse.fail(str(e))


@router.get("/{doc_id}/messages")
def get_messages(doc_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    try:
        svc = DocumentService(db)
        svc.find_accessible(doc_id, user_id)
        messages = db.query(ChatMessage).filter(
            ChatMessage.document_id == doc_id).order_by(ChatMessage.created_at.asc()).all()

        result = []
        for msg in messages:
            sender = db.query(User).filter(User.id == msg.sender_id).first()
            result.append({
                "id": msg.id,
                "documentId": msg.document_id,
                "senderId": msg.sender_id,
                "senderName": sender.username if sender else "Unknown",
                "senderAvatar": sender.avatar_url if sender else "",
                "message": msg.message,
                "messageType": msg.message_type,
                "createdAt": msg.created_at.isoformat() if msg.created_at else None,
            })
        return ApiResponse.ok(result)
    except ValueError as e:
        return ApiResponse.fail(str(e))


@router.post("/{doc_id}/save")
def save_document(doc_id: int, body: DocumentDTO | None = None,
                  user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    try:
        data = body.model_dump(exclude_none=True) if body else None
        result = DocumentService(db).save_snapshot(doc_id, data, user_id)
        return ApiResponse.ok(result)
    except ValueError as e:
        return ApiResponse.fail(str(e))


@router.get("/{doc_id}/snapshots")
def get_snapshots(doc_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    try:
        result = DocumentService(db).get_snapshots(doc_id, user_id)
        return ApiResponse.ok(result)
    except ValueError as e:
        return ApiResponse.fail(str(e))


@router.post("/{doc_id}/snapshots/{snapshot_id}/restore")
def restore_snapshot(doc_id: int, snapshot_id: int,
                     user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    try:
        result = DocumentService(db).restore_snapshot(snapshot_id, doc_id, user_id)
        return ApiResponse.ok(result)
    except ValueError as e:
        return ApiResponse.fail(str(e))
