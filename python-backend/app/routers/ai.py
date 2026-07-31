from typing import Iterator

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.schemas.models import ApiResponse
from app.services.ai_service import AIAgentRunner, ResultFormatter
from app.services.document_service import DocumentService
from app.utils.dependencies import get_current_user_id

router = APIRouter(prefix="/ai", tags=["ai"])


class AskRequest(BaseModel):
    question: str


class RewriteRequest(BaseModel):
    selectedText: str
    mode: str = "polish"


class StreamRequest(BaseModel):
    action: str
    question: str = ""
    selectedText: str = ""
    mode: str = "polish"


def _get_document(doc_id: int, user_id: int, db: Session):
    return DocumentService(db).find_accessible(doc_id, user_id)


@router.post("/documents/{doc_id}/ask")
def ask(
    doc_id: int,
    body: AskRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        document = _get_document(doc_id, user_id, db)
        result = AIAgentRunner(db).run("ask", document, user_id, user_input=body.question)
        return ApiResponse.ok(result)
    except (ValueError, ConnectionError, RuntimeError) as exc:
        return ApiResponse.fail(str(exc))


@router.post("/documents/{doc_id}/summary")
def summary(
    doc_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        document = _get_document(doc_id, user_id, db)
        result = AIAgentRunner(db).run("summary", document, user_id)
        return ApiResponse.ok(result)
    except (ValueError, ConnectionError, RuntimeError) as exc:
        return ApiResponse.fail(str(exc))


@router.post("/documents/{doc_id}/rewrite")
def rewrite(
    doc_id: int,
    body: RewriteRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        document = _get_document(doc_id, user_id, db)
        result = AIAgentRunner(db).run(
            "rewrite",
            document,
            user_id,
            selected_text=body.selectedText,
            mode=body.mode,
        )
        return ApiResponse.ok(result)
    except (ValueError, ConnectionError, RuntimeError) as exc:
        return ApiResponse.fail(str(exc))


@router.get("/documents/{doc_id}/messages")
def get_ai_messages(
    doc_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        _get_document(doc_id, user_id, db)
        return ApiResponse.ok(AIAgentRunner(db).get_history(doc_id, user_id))
    except ValueError as exc:
        return ApiResponse.fail(str(exc))


@router.post("/documents/{doc_id}/stream")
def stream(
    doc_id: int,
    body: StreamRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        document = _get_document(doc_id, user_id, db)
    except ValueError as exc:
        return JSONResponse(
            status_code=403,
            content=ApiResponse.fail(str(exc)).model_dump(),
        )

    def event_stream() -> Iterator[str]:
        try:
            yield from AIAgentRunner(db).stream(
                body.action,
                document,
                user_id,
                user_input=body.question,
                selected_text=body.selectedText,
                mode=body.mode,
            )
        except (ValueError, ConnectionError, RuntimeError) as exc:
            yield ResultFormatter.sse("error", {"message": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
