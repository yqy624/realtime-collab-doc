from typing import Any, TypedDict

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableBranch, RunnableLambda

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
    """LangChain LCEL RAG chain for grounded document Q&A."""

    _ANSWER_PROMPT = PromptTemplate.from_template(
        """You are a grounded knowledge-base agent in a collaborative document system.
Answer only from the supplied reference material.
If the references are insufficient, say that the references are insufficient and do not invent facts.
Answer in Chinese, keep the structure clear, and add [Reference N] after important conclusions.

User question:
{question}

Reference material:
{context}

Give the answer directly."""
    )

    def __init__(self, db):
        self.db = db
        self.rag = RAGService(db)
        self.llm = OllamaLLMClient()
        self.output_parser = StrOutputParser()
        self.chain = self._build_chain()

    def run(
        self,
        question: str,
        user_id: int,
        document_id: int | None = None,
        top_k: int = 6,
    ) -> dict:
        if not question.strip():
            raise ValueError("问题不能为空")

        state = self.chain.invoke(
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
                "orchestration": "langchain_lcel",
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

    def _build_chain(self):
        retrieve = RunnableLambda(self._retrieve_chunks)
        route = RunnableLambda(self._route_evidence)
        grounded = (
            RunnableLambda(self._build_context)
            | RunnableLambda(self._generate_answer)
            | RunnableLambda(self._format_citations)
        )
        refusal = RunnableLambda(self._format_citations)

        return retrieve | route | RunnableBranch(
            (self._has_evidence, grounded),
            refusal,
        )

    @staticmethod
    def _has_evidence(state: AgentState) -> bool:
        return bool(state.get("hits"))

    def _retrieve_chunks(self, state: AgentState) -> AgentState:
        hits = self.rag.search(
            state["question"],
            state["user_id"],
            document_id=state.get("document_id"),
            top_k=state.get("top_k", 6),
        )
        return {**state, "hits": hits}

    @staticmethod
    def _route_evidence(state: AgentState) -> AgentState:
        return {**state, "refusal": not bool(state.get("hits"))}

    @staticmethod
    def _route_after_evidence(state: AgentState) -> str:
        return "grounded" if state.get("hits") else "refuse"

    @staticmethod
    def _build_context(state: AgentState) -> AgentState:
        blocks = []
        for index, hit in enumerate(state.get("hits", []), start=1):
            blocks.append(
                f"[Reference {index}] Document: {hit.title} "
                f"(document ID {hit.document_id}, chunk {hit.chunk_index + 1})\n"
                f"{hit.content}"
            )
        return {**state, "context": "\n\n".join(blocks)}

    def _invoke_answer_model(self, prompt_value) -> dict[str, Any]:
        raw, elapsed_ms = self.llm.generate(prompt_value.to_string())
        return {
            "answer": self.output_parser.invoke(raw or ""),
            "elapsed_ms": elapsed_ms,
            "model": self.llm.model,
        }

    def _generate_answer(self, state: AgentState) -> AgentState:
        answer_chain = self._ANSWER_PROMPT | RunnableLambda(self._invoke_answer_model)
        result = answer_chain.invoke(
            {
                "question": state["question"],
                "context": state.get("context", ""),
            }
        )
        return {
            **state,
            "answer": result["answer"] or "参考资料不足，无法形成可靠回答。",
            "elapsed_ms": result["elapsed_ms"],
            "model": result["model"],
        }

    @staticmethod
    def _format_citations(state: AgentState) -> AgentState:
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
                **state,
                "answer": "当前可访问文档中没有检索到足够依据，暂时无法可靠回答。请更换关键词，或先把相关内容加入可访问文档。",
                "citations": [],
                "elapsed_ms": 0,
                "model": "lexical-rag",
            }
        return {**state, "citations": citations}
