from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import DEFAULT_JWT_SECRET, settings
from app.models.database import (
    Base,
    engine,
    ensure_document_platform_columns,
    ensure_document_share_columns,
    ensure_agent_run_platform_columns,
    ensure_operation_log_platform_columns,
    get_db,
)
from app.models.document import Document
from app.routers import ai, audit, auth, documents, workspaces
from app.routers.ws_handler import websocket_endpoint
from app.services.collaboration_hub import collaboration_hub
from app.utils.jwt import verify_token
from app.init_data import init_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    if (
        settings.app_env.lower() in {"production", "prod"}
        and settings.jwt_secret == DEFAULT_JWT_SECRET
    ):
        raise RuntimeError("JWT_SECRET must be overridden in production")
    if settings.auto_create_tables_on_startup:
        Base.metadata.create_all(bind=engine)
        ensure_document_share_columns()
        ensure_document_platform_columns()
        ensure_operation_log_platform_columns()
        ensure_agent_run_platform_columns()
    if settings.seed_on_startup:
        init_data()
    await collaboration_hub.start()
    yield
    await collaboration_hub.stop()


app = FastAPI(lifespan=lifespan)

allowed_origins = [
    origin.strip()
    for origin in settings.allowed_origins.split(",")
    if origin.strip()
]
allow_all_origins = allowed_origins == ["*"]

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# JWT middleware
@app.middleware("http")
async def jwt_middleware(request: Request, call_next):
    # Skip auth routes and WebSocket
    path = request.url.path
    if (
        path.startswith("/api/auth/")
        or path.startswith("/api/health")
        or path.startswith("/api/ws")
        or path.startswith("/api/share/")
    ):
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = verify_token(token)
        if payload:
            request.state.user_id = payload["userId"]
            request.state.username = payload["sub"]
            return await call_next(request)

    return JSONResponse(
        status_code=401,
        content={"success": False, "data": None, "message": "未授权访问"},
    )


# REST routers
app.include_router(auth.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(workspaces.router, prefix="/api")
app.include_router(audit.router, prefix="/api")


@app.get("/api/health")
def health_check():
    return {"success": True, "data": {"status": "ok"}, "message": "ok"}


# WebSocket endpoint
@app.websocket("/api/ws")
async def ws_route(ws: WebSocket):
    await websocket_endpoint(ws)


# ===== 分享链接访问：GET /api/share/{token} =====
@app.get("/api/share/{token}")
def access_shared_doc(token: str, db: Session = Depends(get_db)):
    from app.services.document_service import DocumentService
    doc = db.query(Document).filter(
        Document.share_token == token,
        Document.deleted_at.is_(None),
    ).first()
    if not doc:
        return JSONResponse(status_code=404, content={"success": False, "data": None, "message": "分享链接无效或已失效"})
    svc = DocumentService(db)
    return JSONResponse(content={"success": True, "data": svc._to_dto(doc), "message": "ok"})
