from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.models.database import Base, engine
from app.routers import auth, documents
from app.routers.ws_handler import websocket_endpoint
from app.utils.jwt import verify_token
from app.init_data import init_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    Base.metadata.create_all(bind=engine)
    # Seed initial data
    init_data()
    yield


app = FastAPI(lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# JWT middleware
@app.middleware("http")
async def jwt_middleware(request: Request, call_next):
    # Skip auth routes and WebSocket
    path = request.url.path
    if path.startswith("/api/auth/") or path.startswith("/api/ws"):
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

# WebSocket endpoint
@app.websocket("/api/ws")
async def ws_route(ws):
    await websocket_endpoint(ws)
