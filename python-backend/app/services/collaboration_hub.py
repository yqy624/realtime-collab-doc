import asyncio
import json
import time
import uuid
from collections import defaultdict
from contextlib import suppress
from typing import Any

from fastapi import WebSocket

from app.config import settings

try:
    import redis.asyncio as redis_async
except ImportError:  # pragma: no cover - optional runtime dependency
    redis_async = None


class InMemoryPresenceStore:
    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = ttl_seconds
        self._connections: dict[int, dict[str, tuple[str, float]]] = defaultdict(dict)

    async def join(self, document_id: int, connection_id: str, username: str) -> list[str]:
        self._connections[document_id][connection_id] = (
            username,
            time.time() + self.ttl_seconds,
        )
        return await self.get_online_users(document_id)

    async def heartbeat(self, document_id: int, connection_id: str) -> list[str]:
        entry = self._connections.get(document_id, {}).get(connection_id)
        if entry:
            self._connections[document_id][connection_id] = (
                entry[0],
                time.time() + self.ttl_seconds,
            )
        return await self.get_online_users(document_id)

    async def leave(self, document_id: int, connection_id: str) -> list[str]:
        users = self._connections.get(document_id)
        if users:
            users.pop(connection_id, None)
            if not users:
                self._connections.pop(document_id, None)
        return await self.get_online_users(document_id)

    async def get_online_users(self, document_id: int) -> list[str]:
        now = time.time()
        users = self._connections.get(document_id, {})
        expired = [key for key, (_, expires_at) in users.items() if expires_at < now]
        for key in expired:
            users.pop(key, None)
        if not users and document_id in self._connections:
            self._connections.pop(document_id, None)
        return sorted({username for username, _ in users.values()})


class RedisPresenceStore:
    def __init__(self, client: Any, prefix: str, ttl_seconds: int):
        self.client = client
        self.prefix = prefix
        self.ttl_seconds = ttl_seconds

    async def join(self, document_id: int, connection_id: str, username: str) -> list[str]:
        await self._write(document_id, connection_id, username)
        return await self.get_online_users(document_id)

    async def heartbeat(self, document_id: int, connection_id: str) -> list[str]:
        key = self._key(document_id)
        raw = await self.client.hget(key, connection_id)
        if raw:
            payload = json.loads(raw)
            await self._write(document_id, connection_id, payload.get("username") or "")
        return await self.get_online_users(document_id)

    async def leave(self, document_id: int, connection_id: str) -> list[str]:
        await self.client.hdel(self._key(document_id), connection_id)
        return await self.get_online_users(document_id)

    async def get_online_users(self, document_id: int) -> list[str]:
        key = self._key(document_id)
        rows = await self.client.hgetall(key)
        now = time.time()
        expired: list[str] = []
        names: set[str] = set()
        for raw_id, raw_value in rows.items():
            connection_id = raw_id.decode("utf-8") if isinstance(raw_id, bytes) else str(raw_id)
            value = raw_value.decode("utf-8") if isinstance(raw_value, bytes) else str(raw_value)
            try:
                payload = json.loads(value)
            except json.JSONDecodeError:
                expired.append(connection_id)
                continue
            if float(payload.get("expiresAt") or 0) < now:
                expired.append(connection_id)
                continue
            username = str(payload.get("username") or "")
            if username:
                names.add(username)
        if expired:
            await self.client.hdel(key, *expired)
        return sorted(names)

    async def _write(self, document_id: int, connection_id: str, username: str) -> None:
        key = self._key(document_id)
        payload = {
            "username": username,
            "expiresAt": time.time() + self.ttl_seconds,
        }
        await self.client.hset(key, connection_id, json.dumps(payload, ensure_ascii=False))
        await self.client.expire(key, self.ttl_seconds * 2)

    def _key(self, document_id: int) -> str:
        return f"{self.prefix}:presence:{document_id}"


class CollaborationHub:
    """Local WebSocket rooms with optional Redis fan-out for multi-instance deploys."""

    def __init__(self):
        self.instance_id = str(uuid.uuid4())
        self._document_connections: dict[int, set[WebSocket]] = defaultdict(set)
        self._connection_docs: dict[str, int] = {}
        self._presence = InMemoryPresenceStore(settings.presence_ttl_seconds)
        self._redis: Any = None
        self._pubsub: Any = None
        self._listener_task: asyncio.Task | None = None

    async def start(self) -> None:
        if not settings.redis_url or redis_async is None:
            return
        self._redis = redis_async.from_url(
            settings.redis_url,
            decode_responses=False,
        )
        await self._redis.ping()
        self._presence = RedisPresenceStore(
            self._redis,
            settings.realtime_channel_prefix,
            settings.presence_ttl_seconds,
        )
        self._pubsub = self._redis.pubsub()
        await self._pubsub.subscribe(self._broadcast_channel)
        self._listener_task = asyncio.create_task(self._listen())

    async def stop(self) -> None:
        if self._listener_task:
            self._listener_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._listener_task
        if self._pubsub:
            await self._pubsub.unsubscribe(self._broadcast_channel)
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()

    def connection_id(self) -> str:
        return f"{self.instance_id}:{uuid.uuid4()}"

    async def join(
        self,
        websocket: WebSocket,
        document_id: int,
        connection_id: str,
        username: str,
    ) -> list[str]:
        self._document_connections[document_id].add(websocket)
        self._connection_docs[connection_id] = document_id
        return await self._presence.join(document_id, connection_id, username)

    async def heartbeat(self, document_id: int, connection_id: str) -> list[str]:
        return await self._presence.heartbeat(document_id, connection_id)

    async def leave(self, websocket: WebSocket, document_id: int, connection_id: str) -> list[str]:
        conns = self._document_connections.get(document_id)
        if conns:
            conns.discard(websocket)
            if not conns:
                self._document_connections.pop(document_id, None)
        self._connection_docs.pop(connection_id, None)
        return await self._presence.leave(document_id, connection_id)

    async def broadcast(self, document_id: int, payload: dict) -> None:
        await self._broadcast_local(document_id, payload)
        if not self._redis:
            return
        envelope = {
            "origin": self.instance_id,
            "documentId": document_id,
            "payload": payload,
        }
        await self._redis.publish(
            self._broadcast_channel,
            json.dumps(envelope, ensure_ascii=False),
        )

    async def send_to_socket(self, websocket: WebSocket, payload: dict) -> None:
        with suppress(Exception):
            await websocket.send_text(json.dumps(payload, ensure_ascii=False))

    async def get_online_users(self, document_id: int) -> list[str]:
        return await self._presence.get_online_users(document_id)

    async def _listen(self) -> None:
        async for message in self._pubsub.listen():
            if message.get("type") != "message":
                continue
            raw = message.get("data")
            text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
            try:
                envelope = json.loads(text)
            except json.JSONDecodeError:
                continue
            if envelope.get("origin") == self.instance_id:
                continue
            await self._broadcast_local(
                int(envelope.get("documentId") or 0),
                envelope.get("payload") or {},
            )

    async def _broadcast_local(self, document_id: int, payload: dict) -> None:
        message = json.dumps(payload, ensure_ascii=False)
        dead: set[WebSocket] = set()
        for websocket in list(self._document_connections.get(document_id, set())):
            try:
                await websocket.send_text(message)
            except Exception:
                dead.add(websocket)
        if dead:
            conns = self._document_connections.get(document_id)
            if conns:
                conns.difference_update(dead)
                if not conns:
                    self._document_connections.pop(document_id, None)

    @property
    def _broadcast_channel(self) -> str:
        return f"{settings.realtime_channel_prefix}:broadcast"


collaboration_hub = CollaborationHub()
