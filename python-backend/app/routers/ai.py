from typing import Iterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.schemas.models import ApiResponse
from app.services.ai_service import AIAgentRunner, ResultFormatter
from app.services.agent_chain import KnowledgeAgent
from app.services.agent_platform_service import AgentPlatformService
from app.services.agent_runtime import AgentRuntime
from app.services.document_service import DocumentService
from app.services.rag_service import RAGService
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


class KnowledgeAgentRequest(BaseModel):
    question: str
    documentId: int | None = None
    workspaceId: int | None = None
    topK: int = 6


class AgentRunRequest(BaseModel):
    goal: str
    documentId: int | None = None
    skillId: int | None = None
    executionMode: str = "inline"


class AgentApprovalRequest(BaseModel):
    approved: bool


class MCPServerRequest(BaseModel):
    workspaceId: int | None = None
    name: str
    transport: str = "stdio"
    connection: dict = Field(default_factory=dict)
    isEnabled: bool = True


def _get_document(doc_id: int, user_id: int, db: Session):
    return DocumentService(db).find_accessible(doc_id, user_id)


@router.get("/knowledge/search")
def search_knowledge(
    q: str,
    documentId: int | None = None,
    workspaceId: int | None = None,
    topK: int = 8,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        if not q.strip():
            raise ValueError("搜索关键词不能为空")
        return ApiResponse.ok(
            RAGService(db).search_response(
                q,
                user_id,
                document_id=documentId,
                workspace_id=workspaceId,
                top_k=topK,
            )
        )
    except ValueError as exc:
        return ApiResponse.fail(str(exc))


@router.get("/knowledge/sources")
def list_knowledge_sources(
    workspaceId: int | None = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return ApiResponse.ok(RAGService(db).list_sources(user_id, workspaceId))
    except ValueError as exc:
        return ApiResponse.fail(str(exc))


@router.post("/knowledge/sources/upload")
async def upload_knowledge_source(
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        form = await request.form()
        file = form.get("file")
        if file is None or not hasattr(file, "read"):
            raise ValueError("请选择要上传的知识库文件")
        workspace_raw = form.get("workspaceId")
        workspace_id = int(workspace_raw) if workspace_raw not in (None, "", "null") else None
        title = str(form.get("title") or "").strip() or None
        content = await file.read()
        result = RAGService(db).import_file(
            file.filename or "upload.txt",
            content,
            file.content_type or "application/octet-stream",
            user_id,
            workspace_id=workspace_id,
            title=title,
        )
        return ApiResponse.ok(result)
    except ValueError as exc:
        return ApiResponse.fail(str(exc))


@router.post("/knowledge/sources/{source_id}/reindex")
def reindex_knowledge_source(
    source_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return ApiResponse.ok(RAGService(db).reindex_source(source_id, user_id))
    except ValueError as exc:
        return ApiResponse.fail(str(exc))


@router.get("/knowledge/jobs")
def list_embedding_jobs(
    workspaceId: int | None = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return ApiResponse.ok(RAGService(db).list_jobs(user_id, workspaceId))
    except ValueError as exc:
        return ApiResponse.fail(str(exc))


@router.get("/knowledge/stats")
def get_knowledge_stats(
    workspaceId: int | None = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return ApiResponse.ok(RAGService(db).coverage_stats(user_id, workspaceId))
    except ValueError as exc:
        return ApiResponse.fail(str(exc))


@router.post("/agent/query")
def query_knowledge_agent(
    body: KnowledgeAgentRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        result = KnowledgeAgent(db).run(
            body.question,
            user_id,
            document_id=body.documentId,
            top_k=body.topK,
        )
        return ApiResponse.ok(result)
    except (ValueError, ConnectionError, RuntimeError) as exc:
        return ApiResponse.fail(str(exc))


@router.get("/agent/tools")
def list_agent_tools(
    workspaceId: int | None = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(AgentPlatformService(db).list_tool_specs(user_id, workspaceId))


@router.get("/agent/skills")
def list_agent_skills(
    workspaceId: int | None = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(AgentPlatformService(db).list_skills(user_id, workspaceId))


@router.get("/agent/mcp/servers")
def list_mcp_servers(
    workspaceId: int | None = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return ApiResponse.ok(AgentPlatformService(db).list_mcp_servers(user_id, workspaceId))
    except ValueError as exc:
        return ApiResponse.fail(str(exc))


@router.post("/agent/mcp/servers")
def create_mcp_server(
    body: MCPServerRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return ApiResponse.ok(AgentPlatformService(db).create_mcp_server(user_id, body.model_dump()))
    except ValueError as exc:
        return ApiResponse.fail(str(exc))


@router.get("/agent/runs")
def list_agent_runs(
    documentId: int | None = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if documentId is not None:
        _get_document(documentId, user_id, db)
    return ApiResponse.ok(AgentRuntime(db).list_runs(user_id, documentId))


@router.post("/agent/run")
def run_agent(
    body: AgentRunRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        result = AgentRuntime(db).start(
            body.goal,
            user_id,
            document_id=body.documentId,
            skill_id=body.skillId,
            execution_mode=body.executionMode,
        )
        return ApiResponse.ok(result)
    except (ValueError, ConnectionError, RuntimeError) as exc:
        return ApiResponse.fail(str(exc))


@router.get("/agent/runs/{run_id}")
def get_agent_run(
    run_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return ApiResponse.ok(AgentRuntime(db).get_run(run_id, user_id))
    except ValueError as exc:
        return ApiResponse.fail(str(exc))


@router.get("/agent/runs/{run_id}/invocations")
def list_agent_run_invocations(
    run_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        AgentRuntime(db).get_run(run_id, user_id)
        return ApiResponse.ok(AgentPlatformService(db).list_invocations(run_id, user_id))
    except ValueError as exc:
        return ApiResponse.fail(str(exc))


@router.post("/agent/runs/{run_id}/approval")
def approve_agent_run(
    run_id: int,
    body: AgentApprovalRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        result = AgentRuntime(db).approve(run_id, user_id, body.approved)
        return ApiResponse.ok(result)
    except (ValueError, ConnectionError, RuntimeError) as exc:
        return ApiResponse.fail(str(exc))


@router.get("/agent/memories")
def list_agent_memories(
    documentId: int | None = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return ApiResponse.ok(AgentRuntime(db).list_memories(user_id, documentId))


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
