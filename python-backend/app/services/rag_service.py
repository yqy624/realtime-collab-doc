import hashlib
import re
from collections import Counter
from dataclasses import dataclass

from sqlalchemy import or_

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_share import DocumentShare


CHUNK_SIZE = 900
CHUNK_OVERLAP = 120
DEFAULT_TOP_K = 6
MIN_SCORE = 0.08


@dataclass
class SearchHit:
    document_id: int
    title: str
    chunk_index: int
    content: str
    score: float
    matched_terms: list[str]

    def to_dict(self) -> dict:
        return {
            "documentId": self.document_id,
            "title": self.title,
            "chunkIndex": self.chunk_index,
            "content": self.content,
            "score": round(self.score, 4),
            "matchedTerms": self.matched_terms,
        }


class RAGService:
    """Small, dependency-light lexical retriever for the document knowledge base.

    The service deliberately keeps indexing local and deterministic. It can later
    be upgraded to hybrid embeddings without changing the API or Agent chain.
    """

    def __init__(self, db):
        self.db = db

    def ensure_document_index(self, document: Document) -> int:
        content = document.content or ""
        digest = self._hash(content)
        existing = (
            self.db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document.id)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )
        if existing and all(row.content_hash == digest for row in existing):
            return len(existing)
        if not content.strip():
            if existing:
                self._delete_loaded_chunks(document.id, existing)
                self.db.commit()
            return 0

        chunks = self.split_text(content)
        self._delete_loaded_chunks(document.id, existing)
        self.db.add_all(
            [
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=index,
                    content=chunk,
                    content_hash=digest,
                )
                for index, chunk in enumerate(chunks)
            ]
        )
        self.db.commit()
        return len(chunks)

    def _delete_loaded_chunks(self, document_id: int, chunks: list[DocumentChunk]) -> None:
        for chunk in chunks:
            self.db.expunge(chunk)
        self.db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).delete(synchronize_session=False)

    def search(
        self,
        query: str,
        user_id: int,
        document_id: int | None = None,
        top_k: int = DEFAULT_TOP_K,
    ) -> list[SearchHit]:
        terms = self.tokenize(query)
        if not terms:
            return []

        documents = self._accessible_documents(user_id, document_id)
        hits: list[SearchHit] = []
        query_phrase = self._normalize(query)
        for document in documents:
            self.ensure_document_index(document)
            chunks = (
                self.db.query(DocumentChunk)
                .filter(DocumentChunk.document_id == document.id)
                .order_by(DocumentChunk.chunk_index.asc())
                .all()
            )
            for chunk in chunks:
                score, matched = self._score(chunk.content, terms, query_phrase)
                if score >= MIN_SCORE:
                    hits.append(
                        SearchHit(
                            document_id=document.id,
                            title=document.title or "Untitled Document",
                            chunk_index=chunk.chunk_index,
                            content=chunk.content,
                            score=score,
                            matched_terms=matched,
                        )
                    )
        hits.sort(key=lambda item: (-item.score, item.title, item.chunk_index))
        return hits[: max(1, min(top_k, 20))]

    def search_response(
        self,
        query: str,
        user_id: int,
        document_id: int | None = None,
        top_k: int = DEFAULT_TOP_K,
    ) -> dict:
        hits = self.search(query, user_id, document_id=document_id, top_k=top_k)
        return {
            "query": query.strip(),
            "total": len(hits),
            "results": [hit.to_dict() for hit in hits],
            "retrieval": {
                "type": "lexical",
                "topK": top_k,
                "documentScope": document_id,
            },
        }

    @staticmethod
    def split_text(text: str) -> list[str]:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", text) if part.strip()]
        if not paragraphs:
            paragraphs = [text.strip()] if text.strip() else []

        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if len(paragraph) <= CHUNK_SIZE:
                candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
                if len(candidate) <= CHUNK_SIZE:
                    current = candidate
                    continue
                if current:
                    chunks.append(current)
                current = paragraph
                continue

            if current:
                chunks.append(current)
                current = ""
            start = 0
            while start < len(paragraph):
                end = min(len(paragraph), start + CHUNK_SIZE)
                piece = paragraph[start:end].strip()
                if piece:
                    chunks.append(piece)
                if end >= len(paragraph):
                    break
                start = max(end - CHUNK_OVERLAP, start + 1)

        if current:
            chunks.append(current)
        return chunks

    @staticmethod
    def tokenize(value: str) -> list[str]:
        normalized = RAGService._normalize(value)
        tokens: list[str] = []
        for token in re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]+", normalized):
            if re.fullmatch(r"[\u4e00-\u9fff]+", token):
                tokens.extend(token)
                tokens.extend(token[index:index + 2] for index in range(len(token) - 1))
            else:
                tokens.append(token)
        return list(dict.fromkeys(token for token in tokens if len(token) > 1 or re.fullmatch(r"[\u4e00-\u9fff]", token)))

    @staticmethod
    def _score(content: str, terms: list[str], query_phrase: str) -> tuple[float, list[str]]:
        normalized = RAGService._normalize(content)
        counts = Counter(RAGService.tokenize(content))
        matched = [term for term in terms if counts.get(term, 0) > 0]
        if not matched:
            return 0.0, []
        coverage = len(matched) / max(len(terms), 1)
        frequency = min(sum(counts[term] for term in matched), 5) / 5
        phrase_bonus = 0.25 if query_phrase and query_phrase in normalized else 0.0
        title_bonus = 0.0
        return min(1.0, coverage * 0.65 + frequency * 0.1 + phrase_bonus + title_bonus), matched

    def _accessible_documents(self, user_id: int, document_id: int | None) -> list[Document]:
        permission_filter = or_(
            Document.creator_id == user_id,
            Document.is_public.is_(True),
            DocumentShare.user_id == user_id,
        )
        query = (
            self.db.query(Document)
            .outerjoin(DocumentShare, DocumentShare.document_id == Document.id)
            .filter(permission_filter)
            .distinct()
        )
        if document_id is not None:
            query = query.filter(Document.id == document_id)
        return query.order_by(Document.updated_at.desc(), Document.id.desc()).all()

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"\s+", " ", (value or "").strip().lower())

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256((value or "").encode("utf-8")).hexdigest()
