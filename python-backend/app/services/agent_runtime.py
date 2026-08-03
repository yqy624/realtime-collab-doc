import difflib
import json
import re
import time
from datetime import datetime
from typing import Any

from app.models.agent_memory import AgentMemory
from app.models.agent_run import AgentRun
from app.models.document import Document
from app.models.document_snapshot import DocumentSnapshot
from app.services.ai_service import OllamaLLMClient
from app.services.document_service import DocumentService
from app.services.rag_service import RAGService
from app.services.web_search_service import WebSearchService
from app.services.weather_service import WeatherService


MAX_PLAN_STEPS = 12
MAX_MEMORY_RESULTS = 5
MAX_OUTPUT_CHARS = 16000
LIVE_SEARCH_RE = re.compile(
    r"(today|latest|current|real[- ]?time|news|breaking|headline|weather|temperature|forecast|"
    r"今天|今日|实时|最新|新闻|资讯|热点|天气|气温|温度|降雨|降雪|天气预报)",
    re.IGNORECASE,
)


class MemoryService:
    """User-scoped long-term and working memory for the document Agent."""

    def __init__(self, db):
        self.db = db

    def recall(self, query: str, user_id: int, document_id: int | None = None) -> list[dict]:
        memories = (
            self.db.query(AgentMemory)
            .filter(AgentMemory.user_id == user_id)
            .order_by(AgentMemory.importance.desc(), AgentMemory.updated_at.desc())
            .all()
        )
        terms = set(RAGService.tokenize(query))
        scored: list[tuple[float, AgentMemory]] = []
        for memory in memories:
            if memory.document_id not in (None, document_id):
                continue
            content_terms = set(RAGService.tokenize(memory.content))
            overlap = len(terms & content_terms)
            score = overlap / max(len(terms), 1) if terms else 0.0
            if score > 0 or not terms:
                scored.append((score, memory))
        scored.sort(key=lambda item: (-item[0], -item[1].importance, -item[1].id))
        return [self._to_dict(memory, score) for score, memory in scored[:MAX_MEMORY_RESULTS]]

    def remember(
        self,
        content: str,
        user_id: int,
        document_id: int | None = None,
        memory_type: str = "working",
        source: str = "agent",
        importance: int = 1,
    ) -> dict:
        normalized = content.strip()
        if not normalized:
            raise ValueError("Memory content cannot be empty")
        memory = AgentMemory(
            user_id=user_id,
            document_id=document_id,
            memory_type=memory_type[:30],
            content=normalized[:MAX_OUTPUT_CHARS],
            source=source[:100],
            importance=max(1, min(5, int(importance))),
        )
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        return self._to_dict(memory, 1.0)

    def list_memories(self, user_id: int, document_id: int | None = None) -> list[dict]:
        query = self.db.query(AgentMemory).filter(AgentMemory.user_id == user_id)
        if document_id is not None:
            query = query.filter(
                (AgentMemory.document_id == document_id)
                | (AgentMemory.document_id.is_(None))
            )
        rows = query.order_by(AgentMemory.updated_at.desc(), AgentMemory.id.desc()).limit(50).all()
        return [self._to_dict(row, None) for row in rows]

    @staticmethod
    def _to_dict(memory: AgentMemory, score: float | None) -> dict:
        return {
            "id": memory.id,
            "userId": memory.user_id,
            "documentId": memory.document_id,
            "type": memory.memory_type,
            "content": memory.content,
            "source": memory.source,
            "importance": memory.importance,
            "score": round(score, 4) if score is not None else None,
            "createdAt": memory.created_at.isoformat() if memory.created_at else None,
            "updatedAt": memory.updated_at.isoformat() if memory.updated_at else None,
        }


class AgentToolRegistry:
    """Permission-aware tools exposed to the planner and executor."""

    def __init__(self, db, user_id: int, document_id: int | None):
        self.db = db
        self.user_id = user_id
        self.document_id = document_id
        self.rag = RAGService(db)
        self.documents = DocumentService(db)
        self.memories = MemoryService(db)
        self.web_search = WebSearchService()
        self.weather = WeatherService()

    @staticmethod
    def specs() -> list[dict]:
        return [
            {
                "name": "recall_memory",
                "description": "Recall user-scoped memories relevant to the current task.",
                "readOnly": True,
                "requiresApproval": False,
                "inputSchema": {"query": "string"},
            },
            {
                "name": "search_knowledge",
                "description": "Search accessible document chunks with permission filtering.",
                "readOnly": True,
                "requiresApproval": False,
                "inputSchema": {"query": "string", "topK": "integer"},
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
            },
            {
                "name": "weather_query",
                "description": "Query current weather and temperature for a city (conditions, highs, lows). Use for weather, temperature, rain, snow, or forecast requests.",
                "readOnly": True,
                "requiresApproval": False,
                "inputSchema": {"city": "string", "days": "integer"},
            },
            {
                "name": "get_current_document",
                "description": "Read the current accessible document and its revision.",
                "readOnly": True,
                "requiresApproval": False,
                "inputSchema": {"documentId": "integer"},
            },
            {
                "name": "list_snapshots",
                "description": "List historical versions of the current document.",
                "readOnly": True,
                "requiresApproval": False,
                "inputSchema": {"documentId": "integer"},
            },
            {
                "name": "generate_diff",
                "description": "Compare a proposed document body with the current revision.",
                "readOnly": True,
                "requiresApproval": False,
                "inputSchema": {"documentId": "integer", "proposedContent": "string"},
            },
            {
                "name": "remember",
                "description": "Persist a user-scoped working memory for future Agent runs.",
                "readOnly": False,
                "requiresApproval": False,
                "inputSchema": {"content": "string", "memoryType": "string", "importance": "integer"},
            },
            {
                "name": "create_snapshot",
                "description": "Create a version snapshot before a document mutation.",
                "readOnly": False,
                "requiresApproval": True,
                "inputSchema": {"documentId": "integer"},
            },
            {
                "name": "apply_document_content",
                "description": "Apply proposed content to the document after user approval.",
                "readOnly": False,
                "requiresApproval": True,
                "inputSchema": {"documentId": "integer", "content": "string"},
            },
        ]

    def execute(self, name: str, args: dict[str, Any], approved: bool = False) -> dict:
        spec = next((item for item in self.specs() if item["name"] == name), None)
        if not spec:
            raise ValueError(f"Unknown Agent tool: {name}")
        if spec["requiresApproval"] and not approved:
            return {
                "requiresApproval": True,
                "tool": name,
                "message": "This tool changes document state and requires user approval.",
            }

        handlers = {
            "recall_memory": self._recall_memory,
            "search_knowledge": self._search_knowledge,
            "web_search": self._web_search,
            "weather_query": self._weather_query,
            "get_current_document": self._get_current_document,
            "list_snapshots": self._list_snapshots,
            "generate_diff": self._generate_diff,
            "remember": self._remember,
            "create_snapshot": self._create_snapshot,
            "apply_document_content": self._apply_document_content,
        }
        return handlers[name](args)

    def _recall_memory(self, args: dict) -> dict:
        query = str(args.get("query") or "")
        return {"memories": self.memories.recall(query, self.user_id, self.document_id)}

    def _search_knowledge(self, args: dict) -> dict:
        query = str(args.get("query") or "")
        if not query.strip():
            return {"results": []}
        top_k = max(1, min(int(args.get("topK") or 6), 20))
        return self.rag.search_response(
            query,
            self.user_id,
            document_id=self.document_id,
            top_k=top_k,
        )

    def _web_search(self, args: dict) -> dict:
        query = str(args.get("query") or "")
        if not query.strip():
            return {"results": []}
        return self.web_search.search(
            query,
            max_results=max(1, min(int(args.get("maxResults") or 5), 10)),
            topic=str(args.get("topic") or "general"),
            date_scope=str(args.get("dateScope") or ""),
            country=str(args.get("country") or ""),
        )

    def _weather_query(self, args: dict) -> dict:
        city = str(args.get("city") or "")
        if not city.strip():
            return {"error": "city is required"}
        return self.weather.search(city, days=max(1, min(int(args.get("days") or 1), 7)))

    def _get_current_document(self, args: dict) -> dict:
        document_id = int(args.get("documentId") or self.document_id or 0)
        document = self.documents.find_accessible(document_id, self.user_id)
        return {
            "documentId": document.id,
            "title": document.title,
            "content": (document.content or "")[:MAX_OUTPUT_CHARS],
            "revision": document.revision,
            "permission": self.documents._get_user_permission(document, self.user_id),
        }

    def _list_snapshots(self, args: dict) -> dict:
        document_id = int(args.get("documentId") or self.document_id or 0)
        return {"snapshots": self.documents.get_snapshots(document_id, self.user_id)}

    def _generate_diff(self, args: dict) -> dict:
        document_id = int(args.get("documentId") or self.document_id or 0)
        document = self.documents.find_accessible(document_id, self.user_id)
        proposed = str(args.get("proposedContent") or "")
        diff = "\n".join(
            difflib.unified_diff(
                (document.content or "").splitlines(),
                proposed.splitlines(),
                fromfile=f"revision-{document.revision}",
                tofile="proposed",
                lineterm="",
            )
        )
        return {
            "documentId": document.id,
            "baseRevision": document.revision,
            "changed": (document.content or "") != proposed,
            "diff": diff[:MAX_OUTPUT_CHARS],
            "proposedContent": proposed[:MAX_OUTPUT_CHARS],
        }

    def _remember(self, args: dict) -> dict:
        return {
            "memory": self.memories.remember(
                str(args.get("content") or ""),
                self.user_id,
                document_id=self.document_id,
                memory_type=str(args.get("memoryType") or "working"),
                importance=int(args.get("importance") or 1),
            )
        }

    def _create_snapshot(self, args: dict) -> dict:
        document_id = int(args.get("documentId") or self.document_id or 0)
        self._assert_write_permission(document_id)
        snapshot = self.documents.save_snapshot(document_id, None, self.user_id)
        return {"snapshot": snapshot}

    def _apply_document_content(self, args: dict) -> dict:
        document_id = int(args.get("documentId") or self.document_id or 0)
        document = self.documents.find_accessible(document_id, self.user_id)
        self._assert_write_permission(document_id)
        content = str(args.get("proposedContent") or args.get("content") or "")
        if not content.strip():
            raise ValueError("Proposed document content cannot be empty")

        previous_revision = document.revision
        self.documents.save_snapshot(document_id, None, self.user_id)
        document.content = content
        document.revision = previous_revision + 1
        document.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(document)
        self.rag.ensure_document_index(document)
        return {
            "documentId": document.id,
            "revision": document.revision,
            "content": document.content,
            "previousRevision": previous_revision,
        }

    def _assert_write_permission(self, document_id: int) -> None:
        document = self.documents.find_accessible(document_id, self.user_id)
        permission = self.documents._get_user_permission(document, self.user_id)
        if permission not in ("owner", "edit"):
            raise ValueError("Agent write tools require owner or edit permission")


class AgentPlanner:
    """Model-assisted planner with a deterministic fallback for local development."""

    def __init__(self, llm: OllamaLLMClient):
        self.llm = llm

    def plan(self, goal: str, document_id: int | None) -> list[dict]:
        try:
            prompt = self._planning_prompt(goal, document_id)
            raw, _ = self.llm.generate(prompt)
            parsed = self._parse_plan(raw)
            if parsed:
                return self._normalize(parsed, goal, document_id)
        except Exception:
            pass
        return self._fallback(goal, document_id)

    def _planning_prompt(self, goal: str, document_id: int | None) -> str:
        tools = [
            "recall_memory",
            "search_knowledge",
            "web_search",
            "weather_query",
            "get_current_document",
            "list_snapshots",
            "generate_diff",
            "remember",
            "create_snapshot",
            "apply_document_content",
        ]
        return (
            "You are an Agent planner. Return JSON only. "
            "Create a short executable plan for the user's goal. "
            "Allowed tool names: "
            f"{', '.join(tools)}. "
            "A model step must use tool name model_generate. "
            "Use web_search for current, latest, real-time, or news requests. "
            "Use weather_query (args: city) for weather, temperature, rain, snow, or forecast requests; "
            "never use web_search for weather. The city argument MUST be the exact Chinese name "
            "from the user's request (e.g. 鹤岗, 上海) — never pinyin, never a translated name. "
            "Write operations must be included only when the user clearly asks to modify the document. "
            'Schema: {"steps":[{"id":"string","tool":"string","args":{},"reason":"string"}]}. '
            f"Current document id: {document_id}. User goal: {goal}"
        )

    @staticmethod
    def _parse_plan(raw: str) -> list[dict]:
        if not raw:
            return []
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            return []
        data = json.loads(raw[start : end + 1])
        steps = data.get("steps") if isinstance(data, dict) else None
        if not isinstance(steps, list):
            return []
        return [step for step in steps if isinstance(step, dict)][:MAX_PLAN_STEPS]

    def _normalize(self, steps: list[dict], goal: str, document_id: int | None) -> list[dict]:
        allowed = {item["name"] for item in AgentToolRegistry.specs()}
        normalized = []
        for index, step in enumerate(steps):
            tool = str(step.get("tool") or "")
            if tool != "model_generate" and tool not in allowed:
                continue
            args = step.get("args") if isinstance(step.get("args"), dict) else {}
            if tool == "weather_query":
                # Granite-class models frequently mangle the city argument (pinyin
                # typos, random strings). Always derive the city from the user's
                # original goal instead of trusting the model's parameter.
                args = dict(args)
                args["city"] = self._weather_city(goal)
            normalized.append(
                {
                    "id": str(step.get("id") or f"step-{index + 1}"),
                    "kind": "model" if tool == "model_generate" else "tool",
                    "tool": tool,
                    "args": args,
                    "reason": str(step.get("reason") or ""),
                    "status": "pending",
                }
            )
        if not any(step["tool"] == "recall_memory" for step in normalized):
            normalized.insert(
                0,
                {
                    "id": "recall-memory",
                    "kind": "tool",
                    "tool": "recall_memory",
                    "args": {"query": goal},
                    "reason": "Load relevant user and document memory.",
                    "status": "pending",
                },
            )
        needs_web_search = self._needs_web_search(goal) and not self._needs_weather(goal)
        if needs_web_search and not any(step["tool"] == "web_search" for step in normalized):
            normalized.insert(
                1,
                {
                    "id": "web-search",
                    "kind": "tool",
                    "tool": "web_search",
                    "args": self._web_search_args(goal),
                    "reason": "Fetch current web/news evidence.",
                    "status": "pending",
                },
            )
        if not any(step["tool"] == "search_knowledge" for step in normalized):
            normalized.insert(
                2 if needs_web_search else 1,
                {
                    "id": "search-knowledge",
                    "kind": "tool",
                    "tool": "search_knowledge",
                    "args": {"query": goal, "topK": 6},
                    "reason": "Retrieve permission-filtered evidence.",
                    "status": "pending",
                },
            )
        if not any(step["kind"] == "model" for step in normalized):
            normalized.append(
                {
                    "id": "model-answer",
                    "kind": "model",
                    "tool": "model_generate",
                    "args": {},
                    "reason": "Synthesize tool results into an answer.",
                    "status": "pending",
                }
            )
        if not any(step["tool"] == "remember" for step in normalized):
            normalized.append(
                {
                    "id": "remember-outcome",
                    "kind": "tool",
                    "tool": "remember",
                    "args": {"content": "$model.answer", "memoryType": "working", "importance": 1},
                    "reason": "Persist a concise result for future runs.",
                    "status": "pending",
                }
            )
        if self._needs_weather(goal) and any(step["tool"] == "weather_query" for step in normalized):
            # Weather requests get their data from weather_query; a web_search
            # step would only surface irrelevant hits and slow the run down.
            normalized = [step for step in normalized if step["tool"] != "web_search"]
        if self._looks_like_edit(goal) and document_id is not None:
            # Rebuild the mutation tail so a model-provided plan cannot apply
            # content before the user-visible diff has been generated.
            remembered = [
                step for step in normalized if step["tool"] == "remember"
            ]
            normalized = [
                step for step in normalized
                if step["tool"] not in ("generate_diff", "apply_document_content", "remember")
            ]
            normalized.extend(
                [
                    {
                        "id": "generate-diff",
                        "kind": "tool",
                        "tool": "generate_diff",
                        "args": {"documentId": document_id, "proposedContent": "$model.proposedContent"},
                        "reason": "Show a reviewable document diff before mutation.",
                        "status": "pending",
                    },
                    {
                        "id": "apply-document",
                        "kind": "tool",
                        "tool": "apply_document_content",
                        "args": {"documentId": document_id, "content": "$model.proposedContent"},
                        "reason": "Apply the approved document change.",
                        "status": "pending",
                    },
                ]
            )
            normalized.extend(
                remembered
                or [
                    {
                        "id": "remember-outcome",
                        "kind": "tool",
                        "tool": "remember",
                        "args": {"content": "$model.answer", "memoryType": "working", "importance": 1},
                        "reason": "Persist a concise result for future runs.",
                        "status": "pending",
                    }
                ]
            )
            if len(normalized) > MAX_PLAN_STEPS:
                required_tail = normalized[-3:]
                available_head = MAX_PLAN_STEPS - len(required_tail)
                normalized = normalized[:available_head] + required_tail
        return normalized[:MAX_PLAN_STEPS]

    def _fallback(self, goal: str, document_id: int | None) -> list[dict]:
        steps = [
            {
                "id": "recall-memory",
                "kind": "tool",
                "tool": "recall_memory",
                "args": {"query": goal},
                "reason": "Load relevant user and document memory.",
                "status": "pending",
            }
        ]
        if document_id is not None:
            steps.append(
                {
                    "id": "read-document",
                    "kind": "tool",
                    "tool": "get_current_document",
                    "args": {"documentId": document_id},
                    "reason": "Read the current document and revision.",
                    "status": "pending",
                }
            )
        if self._needs_weather(goal):
            steps.append(
                {
                    "id": "weather-query",
                    "kind": "tool",
                    "tool": "weather_query",
                    "args": {"city": self._weather_city(goal), "days": 1},
                    "reason": "Fetch current weather for the requested city.",
                    "status": "pending",
                }
            )
        elif self._needs_web_search(goal):
            steps.append(
                {
                    "id": "web-search",
                    "kind": "tool",
                    "tool": "web_search",
                    "args": self._web_search_args(goal),
                    "reason": "Fetch current web/news evidence.",
                    "status": "pending",
                }
            )
        steps.extend(
            [
                {
                    "id": "search-knowledge",
                    "kind": "tool",
                    "tool": "search_knowledge",
                    "args": {"query": goal, "topK": 6},
                    "reason": "Retrieve permission-filtered evidence.",
                    "status": "pending",
                },
                {
                    "id": "model-answer",
                    "kind": "model",
                    "tool": "model_generate",
                    "args": {},
                    "reason": "Synthesize an answer or proposed document content.",
                    "status": "pending",
                },
            ]
        )
        if self._looks_like_edit(goal) and document_id is not None:
            steps.extend(
                [
                    {
                        "id": "generate-diff",
                        "kind": "tool",
                        "tool": "generate_diff",
                        "args": {"documentId": document_id, "proposedContent": "$model.proposedContent"},
                        "reason": "Show a reviewable document diff before mutation.",
                        "status": "pending",
                    },
                    {
                        "id": "apply-document",
                        "kind": "tool",
                        "tool": "apply_document_content",
                        "args": {"documentId": document_id, "content": "$model.proposedContent"},
                        "reason": "Apply the approved document change.",
                        "status": "pending",
                    },
                ]
            )
        steps.append(
            {
                "id": "remember-outcome",
                "kind": "tool",
                "tool": "remember",
                "args": {"content": "$model.answer", "memoryType": "working", "importance": 1},
                "reason": "Persist a concise result for future runs.",
                "status": "pending",
            }
        )
        return steps[:MAX_PLAN_STEPS]

    @staticmethod
    def _needs_web_search(goal: str) -> bool:
        return bool(LIVE_SEARCH_RE.search(goal or ""))

    @staticmethod
    def _needs_weather(goal: str) -> bool:
        return bool(
            re.search(
                r"(天气|气温|温度|降雨|降雪|天气预报|weather|temperature|forecast|rain|snow|多少度)",
                goal or "",
                re.IGNORECASE,
            )
        )

    @staticmethod
    def _weather_city(goal: str) -> str:
        text = re.sub(
            r"(查询|查一下|查查|帮我|请|麻烦|今天|明天|明日|后天|天气|气温|温度|降雨|降雪|预报|怎么样|如何|"
            r"多少|几度|写入|写到|写回|文档|内容|并|把|到|中|里|给|文件|"
            r"weather|temperature|forecast|today|tomorrow|now|the|in|for|of|的|呢|是|和|与)",
            " ",
            goal or "",
            flags=re.IGNORECASE,
        )
        return text.strip() or "北京"

    @staticmethod
    def _web_search_args(goal: str) -> dict:
        date_scope = "today" if re.search(r"(today|今天|今日)", goal or "", re.IGNORECASE) else ""
        topic = "news" if re.search(r"(news|breaking|headline|新闻|资讯|热点)", goal or "", re.IGNORECASE) else "general"
        return {
            "query": goal,
            "maxResults": 5,
            "topic": topic,
            "dateScope": date_scope,
        }

    @staticmethod
    def _looks_like_edit(goal: str) -> bool:
        return bool(
            re.search(
                r"(修改|改写|重写|润色|补充|更新|替换|删除|写入|写到|写回|插入|追加|保存|rewrite|edit|update|polish|write)",
                goal,
                re.IGNORECASE,
            )
        )


class AgentRuntime:
    """Persistent model + tools + memory + planning + execution runtime."""

    def __init__(self, db, llm: OllamaLLMClient | None = None):
        self.db = db
        self.llm = llm or OllamaLLMClient()
        self.memory = MemoryService(db)

    def start(self, goal: str, user_id: int, document_id: int | None = None) -> dict:
        normalized_goal = goal.strip()
        if not normalized_goal:
            raise ValueError("Agent goal cannot be empty")
        if document_id is not None:
            DocumentService(self.db).find_accessible(document_id, user_id)

        plan = AgentPlanner(self.llm).plan(normalized_goal, document_id)
        run = AgentRun(
            user_id=user_id,
            document_id=document_id,
            goal=normalized_goal,
            status="executing",
            plan_json=json.dumps(plan, ensure_ascii=False),
            trace_json="[]",
            memory_json="[]",
            result_text="",
            model=self.llm.model,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return self._execute(run)

    def approve(self, run_id: int, user_id: int, approved: bool) -> dict:
        run = self._get_run(run_id, user_id)
        if run.status != "awaiting_approval":
            raise ValueError("This Agent run is not waiting for approval")
        plan = self._load_json(run.plan_json, [])
        waiting = next((step for step in plan if step.get("status") == "waiting_approval"), None)
        if not waiting:
            raise ValueError("No pending approval step found")
        if not approved:
            waiting["status"] = "rejected"
            run.status = "cancelled"
            run.error = "User rejected the pending Agent action"
            self._save_run(run, plan, self._load_json(run.trace_json, []))
            return self.to_dict(run)
        waiting["approved"] = True
        waiting["status"] = "pending"
        run.status = "executing"
        self._save_run(run, plan, self._load_json(run.trace_json, []))
        return self._execute(run)

    def get_run(self, run_id: int, user_id: int) -> dict:
        return self.to_dict(self._get_run(run_id, user_id))

    def list_runs(self, user_id: int, document_id: int | None = None) -> list[dict]:
        query = (
            self.db.query(AgentRun)
            .filter(AgentRun.user_id == user_id)
        )
        if document_id is not None:
            query = query.filter(AgentRun.document_id == document_id)
        rows = query.order_by(AgentRun.updated_at.desc(), AgentRun.id.desc()).limit(50).all()
        return [self.to_dict(row) for row in rows]

    def list_memories(self, user_id: int, document_id: int | None = None) -> list[dict]:
        return self.memory.list_memories(user_id, document_id)

    @staticmethod
    def tool_specs() -> list[dict]:
        return AgentToolRegistry.specs()

    def _execute(self, run: AgentRun) -> dict:
        plan = self._load_json(run.plan_json, [])
        trace = self._load_json(run.trace_json, [])
        registry = AgentToolRegistry(self.db, run.user_id, run.document_id)
        context: dict[str, Any] = {}

        for step in plan:
            if step.get("status") in ("completed", "rejected"):
                self._merge_step_output(context, step)
                continue
            started = time.perf_counter()
            try:
                if step.get("kind") == "model":
                    output = self._run_model_step(run, context)
                else:
                    args = self._resolve_args(step.get("args") or {}, context)
                    spec = next(item for item in registry.specs() if item["name"] == step["tool"])
                    approved = bool(step.get("approved"))
                    output = registry.execute(step["tool"], args, approved=approved)
                    if output.get("requiresApproval") and not approved:
                        step["status"] = "waiting_approval"
                        step["output"] = output
                        trace.append(
                            self._trace_event(
                                step,
                                "waiting_approval",
                                output,
                                started,
                            )
                        )
                        run.status = "awaiting_approval"
                        self._save_run(run, plan, trace)
                        return self.to_dict(run)

                step["output"] = self._truncate(output)
                step["status"] = "completed"
                self._merge_step_output(context, step)
                trace.append(self._trace_event(step, "completed", output, started))
                self._save_run(run, plan, trace)
            except Exception as exc:
                step["status"] = "failed"
                step["output"] = {"error": str(exc)}
                trace.append(self._trace_event(step, "failed", {"error": str(exc)}, started))
                run.status = "failed"
                run.error = str(exc)
                self._save_run(run, plan, trace)
                return self.to_dict(run)

        answer = str(context.get("model", {}).get("answer") or run.result_text or "")
        run.result_text = answer[:MAX_OUTPUT_CHARS]
        run.status = "completed"
        memory_items = list(context.get("recall_memory", {}).get("memories", []))
        remembered = context.get("remember", {}).get("memory")
        if remembered:
            memory_items.append(remembered)
        run.memory_json = json.dumps(memory_items, ensure_ascii=False)
        self._save_run(run, plan, trace)
        return self.to_dict(run)

    def _run_model_step(self, run: AgentRun, context: dict[str, Any]) -> dict:
        evidence = json.dumps(context, ensure_ascii=False, default=str)[:MAX_OUTPUT_CHARS]
        edit_goal = AgentPlanner._looks_like_edit(run.goal)
        output_schema = (
            '{"answer":"string","proposedContent":"string"}'
            if edit_goal
            else '{"answer":"string"}'
        )
        prompt = (
            "You are the execution model inside a permission-aware document Agent. "
            "Use only the supplied tool outputs. Do not invent document facts. "
            f"Return valid JSON with schema {output_schema}. "
            "When web_search results are present, cite each important news item with title, source URL, and publishedDate if available. "
            "If evidence is insufficient, say so in answer. "
            f"User goal: {run.goal}\nTool outputs:\n{evidence}"
        )
        raw, elapsed_ms = self.llm.generate(prompt)
        parsed = self._parse_json_object(raw)
        if not parsed:
            parsed = {"answer": raw.strip()}
        if edit_goal and not parsed.get("proposedContent"):
            proposed = (
                parsed.get("new_content")
                or parsed.get("newContent")
                or parsed.get("content")
            )
            if proposed:
                parsed["proposedContent"] = proposed
            else:
                # Granite-class models often omit proposedContent despite the schema.
                # Fall back to building the write payload from real tool outputs so
                # the document write is never a no-op / empty overwrite.
                parsed["proposedContent"] = self._auto_proposed_content(context, run.goal)
        parsed["elapsedMs"] = elapsed_ms
        parsed["model"] = self.llm.model
        return parsed

    @staticmethod
    def _auto_proposed_content(context: dict[str, Any], goal: str) -> str:
        """Build document content from tool outputs when the model omits proposedContent."""
        parts: list[str] = []
        weather = context.get("weather_query") or {}
        if weather.get("city"):
            current = weather.get("current") or {}
            daily = weather.get("daily") or []
            lines = [f"【{weather.get('city')}{(' · ' + weather['region']) if weather.get('region') else ''}天气】"]
            if current.get("time"):
                lines.append(f"更新时间: {current['time']}")
            if current.get("condition"):
                lines.append(
                    f"当前天气: {current['condition']}"
                    + (f", 气温 {current['temperatureC']}°C" if current.get("temperatureC") is not None else "")
                    + (f", 体感 {current['apparentTemperatureC']}°C" if current.get("apparentTemperatureC") is not None else "")
                )
            if daily:
                first = daily[0]
                lines.append(
                    f"今日预报: {first.get('condition') or '未知'}, "
                    f"最高 {first.get('maxTempC')}°C / 最低 {first.get('minTempC')}°C"
                )
                for day in daily[1:]:
                    lines.append(
                        f"{day.get('date')}: {day.get('condition') or '未知'}, "
                        f"{day.get('minTempC')}°C ~ {day.get('maxTempC')}°C"
                    )
            parts.append("\n".join(lines))

        search = context.get("web_search") or {}
        results = search.get("results") or []
        # Only attach search results when there is no structured weather data;
        # mixing unrelated search hits into a weather write pollutes the document.
        if not weather.get("city") and results:
            lines = ["【联网搜索结果】"]
            for i, item in enumerate(results[:5], 1):
                title = item.get("title") or ""
                url = item.get("url") or ""
                content = (item.get("content") or "")[:120]
                lines.append(f"{i}. {title}{(' - ' + url) if url else ''}")
                if content:
                    lines.append(f"   {content}")
            parts.append("\n".join(lines))

        if parts:
            return "\n\n".join(parts)
        # Last resort: the model's own answer is the only content we have.
        answer = str((context.get("model") or {}).get("answer") or "") or goal
        return answer.strip()[:MAX_OUTPUT_CHARS]

    def _get_run(self, run_id: int, user_id: int) -> AgentRun:
        run = (
            self.db.query(AgentRun)
            .filter(AgentRun.id == run_id, AgentRun.user_id == user_id)
            .first()
        )
        if not run:
            raise ValueError("Agent run not found")
        return run

    def _save_run(self, run: AgentRun, plan: list[dict], trace: list[dict]) -> None:
        run.plan_json = json.dumps(plan, ensure_ascii=False)
        run.trace_json = json.dumps(trace, ensure_ascii=False)
        run.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(run)

    @staticmethod
    def _resolve_args(value: Any, context: dict[str, Any]) -> Any:
        if isinstance(value, dict):
            return {key: AgentRuntime._resolve_args(item, context) for key, item in value.items()}
        if isinstance(value, list):
            return [AgentRuntime._resolve_args(item, context) for item in value]
        if isinstance(value, str) and value.startswith("$"):
            current: Any = context
            for part in value[1:].split("."):
                if not isinstance(current, dict):
                    return ""
                current = current.get(part)
            return current if current is not None else ""
        return value

    @staticmethod
    def _merge_step_output(context: dict[str, Any], step: dict) -> None:
        key = "model" if step.get("kind") == "model" else step.get("tool")
        context[key] = step.get("output") or {}

    @staticmethod
    def _truncate(value: Any) -> Any:
        if isinstance(value, str):
            return value[:MAX_OUTPUT_CHARS]
        if isinstance(value, dict):
            return {key: AgentRuntime._truncate(item) for key, item in value.items()}
        if isinstance(value, list):
            return [AgentRuntime._truncate(item) for item in value[:20]]
        return value

    @staticmethod
    def _trace_event(step: dict, status: str, output: Any, started: float) -> dict:
        return {
            "stepId": step.get("id"),
            "kind": step.get("kind"),
            "tool": step.get("tool"),
            "status": status,
            "durationMs": int((time.perf_counter() - started) * 1000),
            "outputPreview": AgentRuntime._truncate(output),
        }

    @staticmethod
    def _load_json(raw: str, default: Any) -> Any:
        try:
            return json.loads(raw or "")
        except json.JSONDecodeError:
            return default

    @staticmethod
    def _parse_json_object(raw: str) -> dict:
        if not raw:
            return {}
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            return {}
        try:
            parsed = json.loads(raw[start : end + 1])
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def to_dict(run: AgentRun) -> dict:
        plan = AgentRuntime._load_json(run.plan_json, [])
        trace = AgentRuntime._load_json(run.trace_json, [])
        memories = AgentRuntime._load_json(run.memory_json, [])
        pending = next((step for step in plan if step.get("status") == "waiting_approval"), None)
        return {
            "runId": run.id,
            "goal": run.goal,
            "documentId": run.document_id,
            "status": run.status,
            "plan": plan,
            "trace": trace,
            "memories": memories,
            "result": run.result_text,
            "model": run.model,
            "error": run.error or None,
            "pendingApproval": pending,
            "createdAt": run.created_at.isoformat() if run.created_at else None,
            "updatedAt": run.updated_at.isoformat() if run.updated_at else None,
        }
