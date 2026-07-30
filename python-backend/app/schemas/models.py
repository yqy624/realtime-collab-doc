from typing import Any, Optional

from pydantic import BaseModel


class ApiResponse(BaseModel):
    success: bool
    data: Any = None
    message: str = "ok"

    @staticmethod
    def ok(data: Any, message: str = "ok") -> "ApiResponse":
        return ApiResponse(success=True, data=data, message=message)

    @staticmethod
    def fail(message: str) -> "ApiResponse":
        return ApiResponse(success=False, data=None, message=message)


class AuthRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


class AuthResponse(BaseModel):
    token: str
    userId: int
    username: str
    email: str
    avatarUrl: str


class DocumentDTO(BaseModel):
    id: Optional[int] = None
    title: Optional[str] = None
    content: Optional[str] = None
    creatorId: Optional[int] = None
    isPublic: Optional[bool] = None
    revision: Optional[int] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class ChatMessageDTO(BaseModel):
    id: Optional[int] = None
    documentId: Optional[int] = None
    senderId: Optional[int] = None
    senderName: Optional[str] = None
    senderAvatar: Optional[str] = None
    message: Optional[str] = None
    messageType: Optional[str] = "TEXT"
    createdAt: Optional[str] = None


class SnapshotDTO(BaseModel):
    id: Optional[int] = None
    documentId: Optional[int] = None
    title: Optional[str] = None
    content: Optional[str] = None
    revision: Optional[int] = None
    userId: Optional[int] = None
    userName: Optional[str] = None
    createdAt: Optional[str] = None


class OperationModel(BaseModel):
    type: Optional[str] = None
    position: Optional[int] = None
    length: Optional[int] = None
    content: Optional[str] = None
    revision: Optional[int] = None
    clientId: Optional[str] = None


class CollaborationMessage(BaseModel):
    type: Optional[str] = None
    documentId: Optional[int] = None
    userId: Optional[int] = None
    username: Optional[str] = None
    avatarUrl: Optional[str] = None
    operation: Optional[OperationModel] = None
    chatMessage: Optional[str] = None
    content: Optional[str] = None
    revision: Optional[int] = None
    cursorPosition: Optional[int] = None
    onlineUsers: Optional[list[str]] = None
    timestamp: Optional[str] = None
