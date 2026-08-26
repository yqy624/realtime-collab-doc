import json
from datetime import datetime
from typing import Any

from app.models.mcp_server import MCPServer
from app.models.mcp_tool import MCPTool
from app.models.skill import Skill
from app.models.skill_version import SkillVersion
from app.models.tool_invocation import ToolInvocation
from app.services.audit_service import AuditService
from app.services.platform_service import PlatformService


BUILTIN_TOOL_SPECS = [
    {
        "name": "recall_memory",
        "description": "Recall user-scoped memories relevant to the current task.",
        "readOnly": True,
        "requiresApproval": False,
        "inputSchema": {"query": "string"},
        "toolType": "builtin",
    },
    {
        "name": "search_knowledge",
        "description": "Search accessible document chunks with permission filtering.",
        "readOnly": True,
        "requiresApproval": False,
        "inputSchema": {"query": "string", "topK": "integer"},
        "toolType": "builtin",
    },
    {
        "name": "web_search",
        "description": "Search live web/news sources for current information.",
        "readOnly": True,
        "requiresApproval": False,
        "inputSchema": {
            "query": "string",
            "maxResults": "integer",
            "topic": "string",
            "dateScope": "string",
            "country": "string",
        },
        "toolType": "builtin",
    },
    {
        "name": "weather_query",
        "description": "Query current weather and temperature for a city.",
        "readOnly": True,
        "requiresApproval": False,
        "inputSchema": {"city": "string", "days": "integer"},
        "toolType": "builtin",
    },
    {
        "name": "get_current_document",
        "description": "Read the current accessible document and its revision.",
        "readOnly": True,
        "requiresApproval": False,
        "inputSchema": {"documentId": "integer"},
        "toolType": "builtin",
    },
    {
        "name": "list_snapshots",
        "description": "List historical versions of the current document.",
        "readOnly": True,
        "requiresApproval": False,
        "inputSchema": {"documentId": "integer"},
        "toolType": "builtin",
    },
    {
        "name": "generate_diff",
        "description": "Compare a proposed document body with the current revision.",
        "readOnly": True,
        "requiresApproval": False,
        "inputSchema": {"documentId": "integer", "proposedContent": "string"},
        "toolType": "builtin",
    },
    {
        "name": "remember",
        "description": "Persist a user-scoped working memory for future Agent runs.",
        "readOnly": False,
        "requiresApproval": False,
        "inputSchema": {"content": "string", "memoryType": "string", "importance": "integer"},
        "toolType": "builtin",
    },
    {
        "name": "create_snapshot",
        "description": "Create a version snapshot before a document mutation.",
        "readOnly": False,
        "requiresApproval": True,
        "inputSchema": {"documentId": "integer"},
        "toolType": "builtin",
    },
    {
        "name": "apply_document_content",
        "description": "Apply proposed content to the document after user approval.",
        "readOnly": False,
        "requiresApproval": True,
        "inputSchema": {"documentId": "integer", "content": "string"},
        "toolType": "builtin",
    },
]


DEFAULT_SKILLS = [
    {
        "slug": "knowledge_qa",
        "name": "知识问答",
        "description": "基于可访问文档和当前上下文回答问题，并给出证据来源。",
        "tools": ["recall_memory", "search_knowledge", "web_search", "weather_query", "remember"],
        "prompt": "Answer with permission-safe evidence. Refuse when evidence is insufficient.",
    },
    {
        "slug": "summary",
        "name": "文档总结",
        "description": "总结当前文档的结构、结论、风险与后续行动。",
        "tools": ["recall_memory", "get_current_document", "search_knowledge", "remember"],
        "prompt": "Summarize the current document clearly and preserve unresolved risks.",
    },
    {
        "slug": "polish",
        "name": "改写润色",
        "description": "在生成 diff 后，经批准写回文档。",
        "tools": [
            "recall_memory",
            "get_current_document",
            "generate_diff",
            "create_snapshot",
            "apply_document_content",
            "remember",
        ],
        "prompt": "Improve clarity and style. Never write without a diff and approval.",
    },
    {
        "slug": "weekly_report",
        "name": "周报生成",
        "description": "从文档和知识库中提炼本周进展、风险与下周计划。",
        "tools": ["recall_memory", "search_knowledge", "get_current_document", "remember"],
        "prompt": "Create a concise weekly report with progress, risks, and next actions.",
    },
    {
        "slug": "meeting_minutes",
        "name": "会议纪要",
        "description": "整理会议记录，输出议题、结论、待办和负责人。",
        "tools": ["recall_memory", "get_current_document", "search_knowledge", "remember"],
        "prompt": "Turn meeting notes into decisions, action items, owners, and deadlines.",
    },
]


class AgentPlatformService:
    """Database-backed registry for Skills, MCP definitions, and tool traces."""

    def __init__(self, db):
        self.db = db

    def seed_defaults(self, actor_id: int | None = None) -> None:
        for item in DEFAULT_SKILLS:
            skill = (
                self.db.query(Skill)
                .filter(Skill.workspace_id.is_(None), Skill.slug == item["slug"])
                .first()
            )
            if not skill:
                skill = Skill(
                    workspace_id=None,
                    slug=item["slug"],
                    name=item["name"],
                    description=item["description"],
                    scope="global",
                    input_schema_json=json.dumps({"goal": "string", "documentId": "integer?"}),
                    output_schema_json=json.dumps({"answer": "string", "proposedContent": "string?"}),
                    is_enabled=True,
                    created_by=actor_id,
                )
                self.db.add(skill)
                self.db.flush()
            version = (
                self.db.query(SkillVersion)
                .filter(SkillVersion.skill_id == skill.id, SkillVersion.version == 1)
                .first()
            )
            if not version:
                version = SkillVersion(
                    skill_id=skill.id,
                    version=1,
                    prompt=item["prompt"],
                    tool_dependencies_json=json.dumps(item["tools"], ensure_ascii=False),
                    permission_policy_json=json.dumps(
                        {
                            "writeRequiresApproval": True,
                            "highRiskTools": ["create_snapshot", "apply_document_content"],
                        },
                        ensure_ascii=False,
                    ),
                    status="published",
                    created_by=actor_id,
                )
                self.db.add(version)
        self.db.commit()

    def list_skills(self, user_id: int, workspace_id: int | None = None) -> list[dict]:
        query = self.db.query(Skill).filter(Skill.is_enabled.is_(True))
        if workspace_id is not None:
            try:
                PlatformService(self.db).require_workspace_access(workspace_id, user_id)
                query = query.filter((Skill.workspace_id.is_(None)) | (Skill.workspace_id == workspace_id))
            except ValueError:
                query = query.filter(Skill.workspace_id.is_(None))
        else:
            query = query.filter(Skill.workspace_id.is_(None))
        rows = query.order_by(Skill.workspace_id.asc(), Skill.id.asc()).all()
        return [self.skill_to_dict(row) for row in rows]

    def get_skill(self, skill_id: int | None, user_id: int) -> tuple[Skill | None, SkillVersion | None]:
        if skill_id is None:
            return None, None
        skill = self.db.query(Skill).filter(Skill.id == skill_id, Skill.is_enabled.is_(True)).first()
        if not skill:
            raise ValueError("Skill not found")
        if skill.workspace_id is not None:
            PlatformService(self.db).require_workspace_access(skill.workspace_id, user_id)
        version = (
            self.db.query(SkillVersion)
            .filter(SkillVersion.skill_id == skill.id, SkillVersion.status == "published")
            .order_by(SkillVersion.version.desc(), SkillVersion.id.desc())
            .first()
        )
        return skill, version

    def list_tool_specs(self, user_id: int, workspace_id: int | None = None) -> list[dict]:
        specs = list(BUILTIN_TOOL_SPECS)
        query = self.db.query(MCPTool, MCPServer).join(MCPServer, MCPServer.id == MCPTool.server_id)
        query = query.filter(MCPTool.is_enabled.is_(True), MCPServer.is_enabled.is_(True))
        if workspace_id is not None:
            try:
                PlatformService(self.db).require_workspace_access(workspace_id, user_id)
                query = query.filter((MCPServer.workspace_id.is_(None)) | (MCPServer.workspace_id == workspace_id))
            except ValueError:
                query = query.filter(MCPServer.workspace_id.is_(None))
        else:
            query = query.filter(MCPServer.workspace_id.is_(None))
        for tool, server in query.order_by(MCPTool.name.asc()).all():
            specs.append(
                {
                    "name": f"mcp:{server.name}:{tool.name}",
                    "description": tool.description,
                    "readOnly": tool.read_only,
                    "requiresApproval": tool.requires_approval,
                    "inputSchema": self._json(tool.input_schema_json, {}),
                    "toolType": "mcp",
                    "serverId": server.id,
                    "serverName": server.name,
                }
            )
        return specs

    def list_mcp_servers(self, user_id: int, workspace_id: int | None = None) -> list[dict]:
        query = self.db.query(MCPServer)
        if workspace_id is not None:
            PlatformService(self.db).require_workspace_role(workspace_id, user_id, {"owner", "admin"})
            query = query.filter((MCPServer.workspace_id.is_(None)) | (MCPServer.workspace_id == workspace_id))
        else:
            query = query.filter(MCPServer.workspace_id.is_(None))
        return [self.mcp_server_to_dict(row) for row in query.order_by(MCPServer.id.desc()).all()]

    def create_mcp_server(self, user_id: int, data: dict) -> dict:
        workspace_id = data.get("workspaceId")
        if workspace_id is not None:
            PlatformService(self.db).require_workspace_role(int(workspace_id), user_id, {"owner", "admin"})
        name = str(data.get("name") or "").strip()
        if not name:
            raise ValueError("MCP server name is required")
        row = MCPServer(
            workspace_id=workspace_id,
            name=name[:120],
            transport=str(data.get("transport") or "stdio")[:30],
            connection_json=json.dumps(data.get("connection") or {}, ensure_ascii=False),
            is_enabled=bool(data.get("isEnabled", True)),
            created_by=user_id,
        )
        self.db.add(row)
        self.db.flush()
        AuditService(self.db).record(
            user_id,
            "agent.mcp_server.create",
            "mcp_server",
            target_id=row.id,
            workspace_id=workspace_id,
            after=self.mcp_server_to_dict(row),
        )
        self.db.commit()
        self.db.refresh(row)
        return self.mcp_server_to_dict(row)

    def create_invocation(
        self,
        run,
        tool_name: str,
        tool_type: str,
        args: dict[str, Any],
        approval_status: str,
    ) -> ToolInvocation:
        row = ToolInvocation(
            agent_run_id=run.id,
            skill_id=run.skill_id,
            user_id=run.user_id,
            workspace_id=run.workspace_id,
            document_id=run.document_id,
            tool_name=tool_name[:160],
            tool_type=tool_type[:30],
            status="running",
            approval_status=approval_status,
            input_json=json.dumps(args or {}, ensure_ascii=False, default=str),
            output_json="{}",
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def finish_invocation(
        self,
        invocation: ToolInvocation,
        status: str,
        output: Any = None,
        error: str = "",
        duration_ms: int = 0,
        approval_status: str | None = None,
    ) -> None:
        invocation.status = status[:30]
        invocation.output_json = json.dumps(output or {}, ensure_ascii=False, default=str)
        invocation.error = error
        invocation.duration_ms = duration_ms
        invocation.updated_at = datetime.now()
        if approval_status is not None:
            invocation.approval_status = approval_status
        self.db.commit()

    def list_invocations(self, run_id: int, user_id: int) -> list[dict]:
        rows = (
            self.db.query(ToolInvocation)
            .filter(ToolInvocation.agent_run_id == run_id, ToolInvocation.user_id == user_id)
            .order_by(ToolInvocation.id.asc())
            .all()
        )
        return [self.invocation_to_dict(row) for row in rows]

    def skill_to_dict(self, row: Skill) -> dict:
        version = (
            self.db.query(SkillVersion)
            .filter(SkillVersion.skill_id == row.id, SkillVersion.status == "published")
            .order_by(SkillVersion.version.desc(), SkillVersion.id.desc())
            .first()
        )
        return {
            "id": row.id,
            "workspaceId": row.workspace_id,
            "slug": row.slug,
            "name": row.name,
            "description": row.description,
            "scope": row.scope,
            "inputSchema": self._json(row.input_schema_json, {}),
            "outputSchema": self._json(row.output_schema_json, {}),
            "isEnabled": row.is_enabled,
            "version": version.version if version else None,
            "prompt": version.prompt if version else "",
            "tools": self._json(version.tool_dependencies_json, []) if version else [],
            "createdAt": row.created_at.isoformat() if row.created_at else None,
            "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
        }

    def mcp_server_to_dict(self, row: MCPServer) -> dict:
        tools = self.db.query(MCPTool).filter(MCPTool.server_id == row.id).order_by(MCPTool.name.asc()).all()
        return {
            "id": row.id,
            "workspaceId": row.workspace_id,
            "name": row.name,
            "transport": row.transport,
            "connection": self._json(row.connection_json, {}),
            "isEnabled": row.is_enabled,
            "tools": [self.mcp_tool_to_dict(tool) for tool in tools],
            "createdAt": row.created_at.isoformat() if row.created_at else None,
            "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
        }

    @staticmethod
    def mcp_tool_to_dict(row: MCPTool) -> dict:
        return {
            "id": row.id,
            "serverId": row.server_id,
            "name": row.name,
            "description": row.description,
            "inputSchema": AgentPlatformService._json(row.input_schema_json, {}),
            "readOnly": row.read_only,
            "requiresApproval": row.requires_approval,
            "isEnabled": row.is_enabled,
            "createdAt": row.created_at.isoformat() if row.created_at else None,
            "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
        }

    @staticmethod
    def invocation_to_dict(row: ToolInvocation) -> dict:
        return {
            "id": row.id,
            "agentRunId": row.agent_run_id,
            "skillId": row.skill_id,
            "userId": row.user_id,
            "workspaceId": row.workspace_id,
            "documentId": row.document_id,
            "toolName": row.tool_name,
            "toolType": row.tool_type,
            "status": row.status,
            "approvalStatus": row.approval_status,
            "input": AgentPlatformService._json(row.input_json, {}),
            "output": AgentPlatformService._json(row.output_json, {}),
            "error": row.error or "",
            "durationMs": row.duration_ms,
            "createdAt": row.created_at.isoformat() if row.created_at else None,
            "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
        }

    @staticmethod
    def _json(raw: str | None, default: Any) -> Any:
        try:
            return json.loads(raw or "")
        except json.JSONDecodeError:
            return default
