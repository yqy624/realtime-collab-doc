from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.models.ai_message import AIMessage
from app.services.ai_service import OllamaLLMClient
from app.services.rag_service import RAGService, SearchHit


class AgentState(TypedDict, total=False):
    question: str
    user_id: int
    document_id: int | None
    top_k: int
    hits: list[SearchHit]
    context: str
    answer: str
    citations: list[dict]
    refusal: bool
    elapsed_ms: int
    model: str


class KnowledgeAgent:
    """LangGraph-orchestrated RAG agent for grounded document Q&A."""

    def __init__(self, db):
        self.db = db
        self.rag = RAGService(db)
        self.llm = OllamaLLMClient()
        self.graph = self._build_graph()

    def run(
        self,
        question: str,
        user_id: int,
        document_id: int | None = None,
        top_k: int = 6,
    ) -> dict:
        if not question.strip():
            raise ValueError("问题不能为空")
        state = self.graph.invoke(
            {
                "question": question.strip(),
                "user_id": user_id,
                "document_id": document_id,
                "top_k": top_k,
            }
        )
        result = {
            "question": state["question"],
            "answer": state.get("answer", ""),
            "citations": state.get("citations", []),
            "refusal": state.get("refusal", False),
            "model": state.get("model", self.llm.model),
            "elapsedMs": state.get("elapsed_ms", 0),
            "trace": {
                "workflow": [
                    "retrieve_chunks",
                    "route_evidence",
                    "build_context",
                    "generate_answer",
                    "format_citations",
                ],
                "retrievedChunks": len(state.get("hits", [])),
            },
        }
        self._save_history(
            user_id=user_id,
            document_id=document_id,
            question=result["question"],
            answer=result["answer"],
            model=result["model"],
            elapsed_ms=result["elapsedMs"],
        )
        return result

    def _save_history(
        self,
        user_id: int,
        document_id: int | None,
        question: str,
        answer: str,
        model: str,
        elapsed_ms: int,
    ) -> None:
        if document_id is None:
            return
        self.db.add_all(
            [
                AIMessage(
                    document_id=document_id,
                    user_id=user_id,
                    role="user",
                    action="agent_query",
                    content=question,
                    model=model,
                    elapsed_ms=0,
                ),
                AIMessage(
                    document_id=document_id,
                    user_id=user_id,
                    role="assistant",
                    action="agent_query",
                    content=answer or "",
                    model=model,
                    elapsed_ms=elapsed_ms,
                ),
            ]
        )
        self.db.commit()

    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("retrieve_chunks", self._retrieve_chunks)
        graph.add_node("route_evidence", self._route_evidence)
        graph.add_node("build_context", self._build_context)
        graph.add_node("generate_answer", self._generate_answer)
        graph.add_node("format_citations", self._format_citations)
        graph.set_entry_point("retrieve_chunks")
        graph.add_edge("retrieve_chunks", "route_evidence")
        graph.add_conditional_edges(
            "route_evidence",
            self._route_after_evidence,
            {"grounded": "build_context", "refuse": "format_citations"},
        )
        graph.add_edge("build_context", "generate_answer")
        graph.add_edge("generate_answer", "format_citations")
        graph.add_edge("format_citations", END)
        return graph.compile()

    def _retrieve_chunks(self, state: AgentState) -> dict[str, Any]:
        hits = self.rag.search(
            state["question"],
            state["user_id"],
            document_id=state.get("document_id"),
            top_k=state.get("top_k", 6),
        )
        return {"hits": hits}

    @staticmethod
    def _route_evidence(state: AgentState) -> dict[str, Any]:
        return {"refusal": not bool(state.get("hits"))}

    @staticmethod
    def _route_after_evidence(state: AgentState) -> str:
        return "grounded" if state.get("hits") else "refuse"

    @staticmethod
    def _build_context(state: AgentState) -> dict[str, Any]:
        blocks = []
        for index, hit in enumerate(state.get("hits", []), start=1):
            blocks.append(
                f"[参考资料 {index}] 文档：{hit.title}（文档ID {hit.document_id}，片段 {hit.chunk_index + 1}）\n"
                f"{hit.content}"
            )
        return {"context": "\n\n".join(blocks)}

    def _generate_answer(self, state: AgentState) -> dict[str, Any]:
        prompt = (
            "你是协作文档系统中的知识库 Agent。只能依据参考资料回答问题。"
            "如果参考资料不足以支持结论，要明确说资料不足，不要补充外部事实。"
            "使用中文，回答结构清晰，并在关键结论后使用 [参考资料 N] 标注依据。\n\n"
            f"用户问题：{state['question']}\n\n"
            f"参考资料：\n{state.get('context', '')}\n\n"
            "请直接给出答案。"
        )
        answer, elapsed_ms = self.llm.generate(prompt)
        return {
            "answer": answer or "参考资料不足，无法形成可靠回答。",
            "elapsed_ms": elapsed_ms,
            "model": self.llm.model,
        }

    @staticmethod
    def _format_citations(state: AgentState) -> dict[str, Any]:
        citations = [
            {
                "documentId": hit.document_id,
                "title": hit.title,
                "chunkIndex": hit.chunk_index,
                "content": hit.content,
                "score": round(hit.score, 4),
                "matchedTerms": hit.matched_terms,
            }
            for hit in state.get("hits", [])
        ]
        if state.get("refusal"):
            return {
                "answer": "当前可访问文档中没有检索到足够依据，暂时无法可靠回答。请换一个关键词，或先把相关内容加入可访问文档。",
                "citations": [],
                "elapsed_ms": 0,
                "model": "lexical-rag",
            }
        return {"citations": citations}
