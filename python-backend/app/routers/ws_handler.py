import json
import re
from datetime import datetime
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect, status

from app.models.chat_message import ChatMessage
from app.models.database import SessionLocal
from app.models.operation_log import OperationLog
from app.models.user import User
from app.services.document_service import DocumentService
from app.services.ot_service import OTOperation, OTService
from app.services.session_manager import session_manager
from app.utils.jwt import verify_token

MENTION_PATTERN = re.compile(r"(^|\s)@([\w\-一-龥]+)")

# doc_id -> set of WebSocket connections
_doc_connections: dict[int, set[WebSocket]] = {}
# ws -> username
_ws_user: dict[int, str] = {}


async def websocket_endpoint(ws: WebSocket):
    token = ws.query_params.get("token")
    if not token:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    payload = verify_token(token)
    if not payload:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = payload["userId"]
    username = payload["sub"]

    await ws.accept()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await ws.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Track this connection
        ws_id = id(ws)
        _ws_user[ws_id] = username
        current_doc_id: Optional[int] = None

        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await _send_ws(ws, {"type": "ERROR", "message": "无效的 JSON"})
                continue

            msg_type = msg.get("type")
            doc_id = msg.get("documentId")

            if not doc_id:
                await _send_ws(ws, {"type": "ERROR", "message": "缺少 documentId"})
                continue

            try:
                if msg_type == "JOIN":
                    DocumentService(db).find_accessible(doc_id, user.id)
                    if current_doc_id == doc_id:
                        await _send_ws(ws, {
                            "type": "ERROR",
                            "message": "Already joined to this document",
                        })
                        continue
                    if current_doc_id is not None:
                        old_doc_id = current_doc_id
                        _unregister_connection(ws, old_doc_id)
                        await _handle_leave(db, old_doc_id, user)
                        current_doc_id = None
                    await _handle_join(ws, db, doc_id, user)
                    current_doc_id = doc_id

                elif msg_type == "LEAVE":
                    if current_doc_id != doc_id:
                        raise PermissionError("Join this document before leaving it")
                    _unregister_connection(ws, doc_id)
                    await _handle_leave(db, doc_id, user)
                    current_doc_id = None

                elif msg_type == "EDIT":
                    _assert_joined_document(db, doc_id, user, current_doc_id)
                    await _handle_edit(db, doc_id, user, msg.get("operation") or {})

                elif msg_type == "CHAT":
                    _assert_joined_document(db, doc_id, user, current_doc_id)
                    await _handle_chat(db, doc_id, user, msg.get("chatMessage") or "")

                elif msg_type == "CURSOR":
                    _assert_joined_document(db, doc_id, user, current_doc_id)
                    await _handle_cursor(doc_id, user, msg.get("cursorPosition"))

                else:
                    await _send_ws(ws, {"type": "ERROR", "message": f"Unknown type: {msg_type}"})

            except ValueError as e:
                await _send_ws(ws, {"type": "ERROR", "message": str(e)})
            except PermissionError as e:
                await _send_ws(ws, {"type": "ERROR", "message": str(e)})

    except WebSocketDisconnect:
        pass
    finally:
        # Cleanup
        if current_doc_id:
            _unregister_connection(ws, current_doc_id)
            await _handle_leave(db, current_doc_id, user)
        _ws_user.pop(id(ws), None)
        db.close()


def _register_connection(ws: WebSocket, doc_id: int):
    if doc_id not in _doc_connections:
        _doc_connections[doc_id] = set()
    _doc_connections[doc_id].add(ws)


def _unregister_connection(ws: WebSocket, doc_id: int):
    conns = _doc_connections.get(doc_id)
    if conns:
        conns.discard(ws)
        if not conns:
            del _doc_connections[doc_id]


async def _handle_join(ws: WebSocket, db, doc_id: int, user: User):
    svc = DocumentService(db)
    doc = svc.find_accessible(doc_id, user.id)
    _register_connection(ws, doc_id)
    online = session_manager.join(doc_id, user.username)
    await _broadcast(doc_id, {
        "type": "PRESENCE",
        "documentId": doc_id,
        "onlineUsers": online,
        "timestamp": datetime.now().isoformat(),
    })
    await _send_ws(ws, {
        "type": "SYNC",
        "documentId": doc.id,
        "content": doc.content,
        "revision": doc.revision,
        "timestamp": datetime.now().isoformat(),
    })


async def _handle_leave(db, doc_id: int, user: User):
    online = session_manager.leave(doc_id, user.username)
    await _broadcast(doc_id, {
        "type": "PRESENCE",
        "documentId": doc_id,
        "onlineUsers": online,
        "timestamp": datetime.now().isoformat(),
    })


async def _handle_edit(db, doc_id: int, user: User, op_data: dict):
    if not op_data.get("type"):
        raise ValueError("无效的编辑操作")

    svc = DocumentService(db)
    doc = svc.find_entity(doc_id)

    # 权限校验：仅 owner / edit 权限可编辑，view 权限拒绝
    perm = svc._get_user_permission(doc, user.id)
    if perm not in ("owner", "edit"):
        raise PermissionError("当前用户仅有查看权限")

    incoming = _to_ot_op(op_data)
    base_revision = incoming.revision
    current_revision = doc.revision

    if base_revision > current_revision:
        raise ValueError("文档版本无效")

    transformed = _transform_against_logs(db, doc_id, incoming, base_revision)
    transformed.revision = current_revision

    doc.content = OTService.apply(doc.content, transformed)
    doc.revision = current_revision + 1
    svc.save(doc)

    _save_op_log(db, doc_id, user.id, transformed, doc.revision)

    await _broadcast(doc_id, {
        "type": "EDIT",
        "documentId": doc.id,
        "userId": user.id,
        "username": user.username,
        "avatarUrl": user.avatar_url or "",
        "content": doc.content,
        "revision": doc.revision,
        "operation": _op_to_dict(transformed),
        "timestamp": datetime.now().isoformat(),
    })


async def _handle_chat(db, doc_id: int, user: User, chat_text: str):
    DocumentService(db).find_accessible(doc_id, user.id)
    if not chat_text.strip():
        raise ValueError("消息不能为空")

    msg = ChatMessage(
        document_id=doc_id,
        sender_id=user.id,
        message=chat_text.strip(),
        message_type="TEXT",
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    payload = {
        "type": "CHAT",
        "id": msg.id,
        "documentId": msg.document_id,
        "senderId": user.id,
        "senderName": user.username,
        "senderAvatar": user.avatar_url or "",
        "message": msg.message,
        "messageType": msg.message_type,
        "createdAt": msg.created_at.isoformat() if msg.created_at else None,
    }
    await _broadcast(doc_id, payload)
    _handle_mentions(doc_id, user, payload)


async def _handle_cursor(doc_id: int, user: User, cursor_pos):
    await _broadcast(doc_id, {
        "type": "CURSOR",
        "documentId": doc_id,
        "userId": user.id,
        "username": user.username,
        "avatarUrl": user.avatar_url or "",
        "cursorPosition": cursor_pos,
        "timestamp": datetime.now().isoformat(),
    })


def _assert_joined_document(db, doc_id: int, user: User, current_doc_id: int | None) -> None:
    if current_doc_id != doc_id:
        raise PermissionError("Join this document before sending messages")
    DocumentService(db).find_accessible(doc_id, user.id)


def _extract_mentions(text: str) -> set[str]:
    return {m.group(2) for m in MENTION_PATTERN.finditer(text)}


def _handle_mentions(doc_id: int, sender: User, payload: dict):
    online = session_manager.get_online_users(doc_id)
    mentioned = _extract_mentions(payload.get("message", ""))
    mentioned &= set(online)
    mentioned.discard(sender.username)

    if not mentioned:
        return

    # For now, mentioned users see the chat message in broadcast anyway
    # This keeps the @mention tracking for future personalized notifications
    pass


async def _broadcast(doc_id: int, data: dict):
    """Send JSON to every WebSocket connected to this document."""
    message = json.dumps(data, ensure_ascii=False)
    dead = set()
    for ws in _doc_connections.get(doc_id, set()):
        try:
            await ws.send_text(message)
        except Exception:
            dead.add(ws)
    if dead:
        _doc_connections[doc_id] -= dead
        if not _doc_connections[doc_id]:
            del _doc_connections[doc_id]


async def _send_ws(ws: WebSocket, data: dict):
    try:
        await ws.send_text(json.dumps(data, ensure_ascii=False))
    except Exception:
        pass


def _to_ot_op(data: dict) -> OTOperation:
    return OTOperation(
        type_=data.get("type"),
        position=data.get("position", 0),
        length=data.get("length", 0),
        content=data.get("content", ""),
        revision=data.get("revision", 0),
        client_id=data.get("clientId", ""),
    )


def _op_to_dict(op: OTOperation) -> dict:
    return {
        "type": op.type,
        "position": op.position,
        "length": op.length,
        "content": op.content,
        "revision": op.revision,
        "clientId": op.client_id,
    }


def _transform_against_logs(db, doc_id: int, incoming: OTOperation, base_revision: int) -> OTOperation:
    transformed = incoming
    logs = (db.query(OperationLog)
            .filter(OperationLog.document_id == doc_id, OperationLog.revision > base_revision)
            .order_by(OperationLog.revision.asc()).all())
    for log in logs:
        applied = OTOperation(
            type_=log.operation_type,
            position=log.position,
            length=0,
            content=log.content or "",
            revision=log.revision,
        )
        transformed = OTService.transform(transformed, applied)
    return transformed


def _save_op_log(db, doc_id: int, user_id: int, op: OTOperation, revision: int):
    content = "#" * max(op.length, 0) if op.type == "DELETE" and op.length else (op.content or "")
    db.add(OperationLog(
        document_id=doc_id,
        user_id=user_id,
        operation_type=op.type,
        position=op.position or 0,
        content=content,
        revision=revision,
    ))
