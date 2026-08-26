# Platform Architecture Roadmap

This project is moving from a single collaborative document app toward a workspace-based collaboration platform with first-class Agent capabilities.

## Phase 1: Workspace Foundation

Implemented in this iteration:

- Workspace model: users can own and join multiple workspaces.
- Workspace members: `owner`, `admin`, `member`, and `viewer` roles.
- Folder model: documents can be grouped inside a workspace.
- Document location fields: `workspace_id`, `folder_id`, and `content_format`.
- Document permission model: `manage`, `edit`, `comment`, and `view`.
- Workspace APIs for listing/creating workspaces, members, and folders.
- Document APIs accept `workspaceId` and `folderId` filters.
- RAG visibility now includes workspace and document-level permissions.
- Frontend home page now behaves like a workspace console.

The old owner/share/public access flow remains compatible.

## Phase 2: Collaboration Scale-Out

The current WebSocket connection registry is in-process memory. It works for a single backend instance, but it will not scale horizontally.

Implemented foundation:

- Added `CollaborationHub` as the shared WebSocket room and broadcast abstraction.
- Added optional Redis Pub/Sub fan-out for multi-backend document broadcasts.
- Added Redis-backed presence store with TTL cleanup when `REDIS_URL` is configured.
- Kept in-memory fallback for local development when Redis is not configured.
- Added WebSocket heartbeat support for refreshing presence.
- Added edit `requestId`, `clientId`, and `serverInstance` diagnostics in operation logs.
- Updated Docker Compose with a Redis service and backend `REDIS_URL`.
- Added regression tests for multiple connections, heartbeat refresh, and stale presence cleanup.

Recommended next changes:

- Split collaboration messages into typed event handlers.
- Add per-document rate limits for edit and cursor traffic.
- Add Redis integration tests with two backend processes.

## Phase 3: Schema and Data Operations

The backend currently creates tables on startup and patches columns manually. That is fine for early local development, but not for long-term production.

Recommended next changes:

Implemented foundation:

- Added Alembic migration scaffolding under `python-backend/alembic`.
- Added a phase-three migration file for audit logs, soft delete fields, and platform indexes.
- Added `AuditLog` model and `AuditService` for append-only governance logs.
- Added document soft delete fields: `deleted_at`, `deleted_by`, and `delete_reason`.
- Changed normal document deletion into a recycle-bin move.
- Added restore and permanent-delete APIs for deleted documents.
- Added `/api/audit/logs` for user-scoped audit log inspection.
- Added workspace-scoped audit log inspection for workspace owners and admins.
- Updated the workspace console with a recycle-bin view.
- Added a workspace governance-log view in the frontend console.
- Added explicit `seed-db`, `reset-db`, and `migrate-db` scripts for local and deployment operations.
- Added startup switches: `AUTO_CREATE_TABLES_ON_STARTUP` and `SEED_ON_STARTUP`.
- Added regression tests for soft delete, restore, deleted-document access, and audit records.

Recommended next changes:

- Add recycle-bin retention policy and scheduled cleanup.
- Add CI migration checks that run `scripts/migrate-db.ps1` against an empty database.
- Expand audit filters by document, actor, action, and time range.

## Phase 4: Agent Platform

The Agent runtime already has planning, tools, memory, trace, and approval. The next step is to make it extensible.

Implemented foundation:

- Added `skills` and `skill_versions` tables.
- Added default reusable Skills: knowledge Q&A, summary, polish, weekly report, and meeting minutes.
- Added `mcp_servers` and `mcp_tools` tables as the workspace-scoped MCP configuration registry.
- Added `tool_invocations` table for model/tool input, output, duration, approval status, and errors.
- Added `agent_runs.workspace_id`, `agent_runs.skill_id`, and `agent_runs.execution_mode`.
- Agent runs now use `queued`, `running`, `awaiting_approval`, `completed`, `failed`, and `cancelled` statuses.
- Agent execution can receive a `skillId`; skill prompts and tool dependency lists influence planning.
- Built-in tool specs are exposed through a platform registry, with MCP tool records included in the same API shape.
- Added Agent APIs for Skills, MCP server definitions, and run invocations.
- Added frontend Skill selection in the editor Agent panel.
- Added frontend Agent Center overview for Skills, tools, and recent runs.

Recommended next changes:

- Execute Agent runs asynchronously through a task queue worker instead of inline execution.
- Add live Agent event streaming through WebSocket or SSE.
- Implement real MCP connector execution for configured MCP tools.
- Add per-space Skill creation/editing UI and version publishing flow.
- Add workspace-scoped Agent memory and RAG collection controls.

## Phase 5: Knowledge and RAG

The current RAG retriever is deterministic lexical search. It is reliable but limited.

Recommended next changes:

- Add embedding generation as a background indexing job.
- Store vectors in pgvector, Milvus, Qdrant, or another vector backend.
- Use hybrid retrieval: lexical + vector + recency + permission filtering.
- Add file ingestion for PDF, DOCX, Markdown, and plain text.
- Show citations, chunk previews, and permission-safe source links in the UI.
