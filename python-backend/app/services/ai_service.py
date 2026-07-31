import json
import time
from dataclasses import dataclass
from typing import Iterator
from urllib import error, request

from app.config import settings
from app.models.ai_message import AIMessage


MAX_CONTEXT_CHARS = 12000


@dataclass
class AgentContext:
    document_id: int
    title: str
    content: str
    selected_text: str
    user_input: str
    mode: str


class ContextBuilder:
    def build(self, document, user_input: str = "", selected_text: str = "", mode: str = "") -> AgentContext:
        content = document.content or ""
        if len(content) > MAX_CONTEXT_CHARS:
            content = content[:MAX_CONTEXT_CHARS] + "\n\n[文档内容过长，已截取前 12000 字。]"

        return AgentContext(
            document_id=document.id,
            title=document.title or "Untitled Document",
            content=content,
            selected_text=selected_text or "",
            user_input=user_input or "",
            mode=mode or "",
        )


class PromptBuilder:
    def build(self, action: str, context: AgentContext) -> str:
        base = (
            "你是一个协作文档系统中的本地 AI Agent，只能基于用户提供的文档内容回答。\n"
            "要求：使用中文；结论清晰；不要编造文档中不存在的事实；输出可直接复制到文档中。\n\n"
            f"文档标题：{context.title}\n"
            f"文档正文：\n{context.content}\n"
        )

        if action == "summary":
            return base + "\n任务：总结全文，输出 3-6 条要点，并给出一个简短结论。"

        if action == "rewrite":
            source = context.selected_text.strip()
            if not source:
                raise ValueError("请先选择或输入需要处理的文本")
            instruction = self._rewrite_instruction(context.mode)
            return (
                base
                + "\n需要处理的选中文本：\n"
                + source
                + f"\n\n任务：{instruction}。只输出处理后的文本，不要解释处理过程。"
            )

        if action == "ask":
            question = context.user_input.strip()
            if not question:
                raise ValueError("问题不能为空")
            return base + f"\n用户问题：{question}\n\n任务：基于文档内容回答用户问题。"

        raise ValueError("不支持的 AI 动作")

    @staticmethod
    def _rewrite_instruction(mode: str) -> str:
        mapping = {
            "polish": "润色这段文字，使表达更自然、正式、准确",
            "expand": "扩写这段文字，补充必要细节，但保持原意",
            "translate": "将这段文字翻译成英文",
        }
        return mapping.get(mode or "polish", mapping["polish"])


class OllamaLLMClient:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        if self.model.endswith(":cloud"):
            raise ValueError("AI 仅支持本地 Ollama 模型，当前配置不能使用云端模型")

    def generate(self, prompt: str) -> tuple[str, int]:
        started = time.perf_counter()
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        try:
            with request.urlopen(self._request(payload), timeout=180) as response:
                body = json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:
            raise ConnectionError("无法连接本地 Ollama，请确认 ollama 服务正在运行") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("Ollama 返回内容无法解析") from exc

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return (body.get("response") or "").strip(), elapsed_ms

    def stream_generate(self, prompt: str) -> Iterator[str]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
        }
        try:
            with request.urlopen(self._request(payload), timeout=180) as response:
                for raw_line in response:
                    if not raw_line:
                        continue
                    try:
                        chunk = json.loads(raw_line.decode("utf-8"))
                    except json.JSONDecodeError:
                        continue
                    text = chunk.get("response") or ""
                    if text:
                        yield text
                    if chunk.get("done"):
                        break
        except error.URLError as exc:
            raise ConnectionError("无法连接本地 Ollama，请确认 ollama 服务正在运行") from exc

    def _request(self, payload: dict) -> request.Request:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return request.Request(
            f"{self.base_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )


class ResultFormatter:
    @staticmethod
    def to_response(action: str, model: str, content: str, elapsed_ms: int) -> dict:
        return {
            "action": action,
            "model": model,
            "content": content,
            "elapsedMs": elapsed_ms,
        }

    @staticmethod
    def sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class AIAgentRunner:
    def __init__(self, db):
        self.db = db
        self.context_builder = ContextBuilder()
        self.prompt_builder = PromptBuilder()
        self.client = OllamaLLMClient()
        self.formatter = ResultFormatter()

    def run(
        self,
        action: str,
        document,
        user_id: int,
        user_input: str = "",
        selected_text: str = "",
        mode: str = "",
    ) -> dict:
        context = self.context_builder.build(document, user_input, selected_text, mode)
        prompt = self.prompt_builder.build(action, context)
        self._save_message(document.id, user_id, "user", action, self._user_message(action, context), 0)
        content, elapsed_ms = self.client.generate(prompt)
        self._save_message(document.id, user_id, "assistant", action, content, elapsed_ms)
        return self.formatter.to_response(action, self.client.model, content, elapsed_ms)

    def stream(
        self,
        action: str,
        document,
        user_id: int,
        user_input: str = "",
        selected_text: str = "",
        mode: str = "",
    ) -> Iterator[str]:
        context = self.context_builder.build(document, user_input, selected_text, mode)
        prompt = self.prompt_builder.build(action, context)
        self._save_message(document.id, user_id, "user", action, self._user_message(action, context), 0)

        started = time.perf_counter()
        chunks: list[str] = []
        yield self.formatter.sse("meta", {"action": action, "model": self.client.model})

        try:
            for text in self.client.stream_generate(prompt):
                chunks.append(text)
                yield self.formatter.sse("chunk", {"content": text})
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            content = "".join(chunks).strip()
            self._save_message(document.id, user_id, "assistant", action, content, elapsed_ms)
            yield self.formatter.sse("done", self.formatter.to_response(action, self.client.model, content, elapsed_ms))
        except Exception as exc:
            yield self.formatter.sse("error", {"message": str(exc)})

    def get_history(self, document_id: int, user_id: int) -> list[dict]:
        rows = (
            self.db.query(AIMessage)
            .filter(AIMessage.document_id == document_id, AIMessage.user_id == user_id)
            .order_by(AIMessage.created_at.asc(), AIMessage.id.asc())
            .all()
        )
        return [self._to_dto(row) for row in rows]

    def _save_message(
        self,
        document_id: int,
        user_id: int,
        role: str,
        action: str,
        content: str,
        elapsed_ms: int,
    ) -> None:
        self.db.add(
            AIMessage(
                document_id=document_id,
                user_id=user_id,
                role=role,
                action=action,
                content=content or "",
                model=self.client.model,
                elapsed_ms=elapsed_ms,
            )
        )
        self.db.commit()

    @staticmethod
    def _user_message(action: str, context: AgentContext) -> str:
        if action == "summary":
            return "总结全文"
        if action == "rewrite":
            return f"{context.mode or 'polish'}: {context.selected_text}"
        return context.user_input

    @staticmethod
    def _to_dto(row: AIMessage) -> dict:
        return {
            "id": row.id,
            "documentId": row.document_id,
            "userId": row.user_id,
            "role": row.role,
            "action": row.action,
            "content": row.content,
            "model": row.model,
            "elapsedMs": row.elapsed_ms,
            "createdAt": row.created_at.isoformat() if row.created_at else None,
        }
