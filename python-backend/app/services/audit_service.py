import json
from typing import Any

from app.models.audit_log import AuditLog


class AuditService:
    """Small append-only audit logger for platform governance actions."""

    def __init__(self, db):
        self.db = db

    def record(
        self,
        actor_id: int,
        action: str,
        target_type: str,
        target_id: int | None = None,
        workspace_id: int | None = None,
        document_id: int | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        commit: bool = False,
    ) -> AuditLog:
        row = AuditLog(
            actor_id=actor_id,
            action=action[:80],
            target_type=target_type[:80],
            target_id=target_id,
            workspace_id=workspace_id,
            document_id=document_id,
            before_json=json.dumps(before or {}, ensure_ascii=False, default=str),
            after_json=json.dumps(after or {}, ensure_ascii=False, default=str),
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False, default=str),
        )
        self.db.add(row)
        if commit:
            self.db.commit()
            self.db.refresh(row)
        return row

    def list_for_actor(self, actor_id: int, limit: int = 100) -> list[dict]:
        rows = (
            self.db.query(AuditLog)
            .filter(AuditLog.actor_id == actor_id)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(max(1, min(limit, 200)))
            .all()
        )
        return [self.to_dict(row) for row in rows]

    def list_for_workspace(self, workspace_id: int, limit: int = 100) -> list[dict]:
        rows = (
            self.db.query(AuditLog)
            .filter(AuditLog.workspace_id == workspace_id)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(max(1, min(limit, 200)))
            .all()
        )
        return [self.to_dict(row) for row in rows]

    @staticmethod
    def to_dict(row: AuditLog) -> dict:
        return {
            "id": row.id,
            "actorId": row.actor_id,
            "action": row.action,
            "targetType": row.target_type,
            "targetId": row.target_id,
            "workspaceId": row.workspace_id,
            "documentId": row.document_id,
            "before": AuditService._parse(row.before_json),
            "after": AuditService._parse(row.after_json),
            "metadata": AuditService._parse(row.metadata_json),
            "createdAt": row.created_at.isoformat() if row.created_at else None,
        }

    @staticmethod
    def _parse(raw: str) -> dict:
        try:
            parsed = json.loads(raw or "{}")
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
