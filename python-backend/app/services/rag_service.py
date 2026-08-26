import hashlib
import json
import math
import re
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO

from sqlalchemy import or_

from app.config import settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_share import DocumentShare
from app.models.embedding_job import EmbeddingJob
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_source import KnowledgeSource
from app.models.workspace_member import WorkspaceMember
from app.services.platform_service import PlatformService


CHUNK_SIZE = 900
CHUNK_OVERLAP = 120
DEFAULT_TOP_K = 6
MIN_SCORE = 0.08
LOCAL_VECTOR_DIMENSIONS = 64
SUPPORTED_IMPORT_TYPES = {".txt", ".md", ".markdown", ".docx", ".pdf"}


@dataclass
class SearchHit:
    document_id: int
    title: str
    chunk_index: int
    content: str
    score: float
    matched_terms: list[str]
    source_id: int | None = None
    source_type: str = "document"
    workspace_id: int | None = None
    page_number: int | None = None
    location_label: str = ""

    def to_dict(self) -> dict:
        return {
            "documentId": self.document_id,
            "title": self.title,
            "chunkIndex": self.chunk_index,
            "content": self.content,
            "score": round(self.score, 4),
            "matchedTerms": self.matched_terms,
            "sourceId": self.source_id,
            "sourceType": self.source_type,
            "workspaceId": self.workspace_id,
            "pageNumber": self.page_number,
            "locationLabel": self.location_label,
            "citation": {
                "sourceId": self.source_id,
                "sourceType": self.source_type,
                "title": self.title,
                "documentId": self.document_id,
                "chunkIndex": self.chunk_index,
                "pageNumber": self.page_number,
                "locationLabel": self.location_label,
            },
        }


class RAGService:
    """Small, dependency-light lexical retriever for the document knowledge base.

    The service deliberately keeps indexing local and deterministic. It can later
    be upgraded to hybrid embeddings without changing the API or Agent chain.
    """

    def __init__(self, db):
        self.db = db

    def ensure_document_index(self, document: Document, requested_by: int | None = None) -> int:
        content = document.content or ""
        digest = self._hash(content)
        existing = (
            self.db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document.id)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )
        if existing and all(row.content_hash == digest for row in existing):
            self._index_document_source(document, digest, requested_by or document.creator_id)
            return len(existing)
        if not content.strip():
            if existing:
                self._delete_loaded_chunks(document.id, existing)
            self._clear_document_knowledge_index(document.id)
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
        self._index_document_source(document, digest, requested_by or document.creator_id)
        return len(chunks)

    def _delete_loaded_chunks(self, document_id: int, chunks: list[DocumentChunk]) -> None:
        for chunk in chunks:
            self.db.expunge(chunk)
        self.db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).delete(synchronize_session=False)

    def _clear_document_knowledge_index(self, document_id: int) -> None:
        source_ids = [
            row.id
            for row in self.db.query(KnowledgeSource.id)
            .filter(KnowledgeSource.document_id == document_id)
            .all()
        ]
        if not source_ids:
            return
        self.db.query(KnowledgeChunk).filter(KnowledgeChunk.source_id.in_(source_ids)).delete()
        self.db.query(EmbeddingJob).filter(EmbeddingJob.source_id.in_(source_ids)).delete()
        self.db.query(KnowledgeSource).filter(KnowledgeSource.id.in_(source_ids)).delete()

    def search(
        self,
        query: str,
        user_id: int,
        document_id: int | None = None,
        top_k: int = DEFAULT_TOP_K,
        workspace_id: int | None = None,
    ) -> list[SearchHit]:
        terms = self.tokenize(query)
        if not terms:
            return []

        documents = self._accessible_documents(user_id, document_id, workspace_id)
        hits: list[SearchHit] = []
        query_phrase = self._normalize(query)
        query_vector = self._embed(query)
        for document in documents:
            self.ensure_document_index(document, requested_by=user_id)

        for source in self._accessible_sources(user_id, document_id, workspace_id):
            chunks = self.db.query(KnowledgeChunk).filter(
                KnowledgeChunk.source_id == source.id,
            ).order_by(KnowledgeChunk.chunk_index.asc()).all()
            for chunk in chunks:
                lexical_score, matched = self._score(chunk.content, terms, query_phrase)
                vector_score = self._cosine(query_vector, self._loads_vector(chunk.embedding_json))
                rerank_bonus = self._rerank_bonus(source.title, chunk.content, query_phrase, matched)
                score = min(1.0, lexical_score * 0.55 + vector_score * 0.35 + rerank_bonus)
                if score >= MIN_SCORE:
                    hits.append(self._hit_from_chunk(source, chunk, score, matched))
        hits.sort(key=lambda item: (-item.score, item.title, item.chunk_index))
        return hits[: max(1, min(top_k, 20))]

    def search_response(
        self,
        query: str,
        user_id: int,
        document_id: int | None = None,
        top_k: int = DEFAULT_TOP_K,
        workspace_id: int | None = None,
    ) -> dict:
        hits = self.search(
            query,
            user_id,
            document_id=document_id,
            top_k=top_k,
            workspace_id=workspace_id,
        )
        citations = [hit.to_dict()["citation"] for hit in hits]
        return {
            "query": query.strip(),
            "total": len(hits),
            "results": [hit.to_dict() for hit in hits],
            "citations": citations,
            "retrieval": {
                "type": "hybrid",
                "stages": ["keyword", "local_vector", "permission_filter", "rerank"],
                "vectorBackend": settings.rag_vector_backend,
                "topK": top_k,
                "documentScope": document_id,
                "workspaceScope": workspace_id,
            },
        }

    def list_sources(self, user_id: int, workspace_id: int | None = None) -> list[dict]:
        return [
            self._source_to_dict(source)
            for source in self._accessible_sources(user_id, workspace_id=workspace_id)
        ]

    def list_jobs(self, user_id: int, workspace_id: int | None = None) -> list[dict]:
        source_ids = [source.id for source in self._accessible_sources(user_id, workspace_id=workspace_id)]
        if not source_ids:
            return []
        rows = (
            self.db.query(EmbeddingJob)
            .filter(EmbeddingJob.source_id.in_(source_ids))
            .order_by(EmbeddingJob.created_at.desc(), EmbeddingJob.id.desc())
            .limit(100)
            .all()
        )
        return [self._job_to_dict(row) for row in rows]

    def coverage_stats(self, user_id: int, workspace_id: int | None = None) -> dict:
        sources = self._accessible_sources(user_id, workspace_id=workspace_id)
        source_ids = [source.id for source in sources]
        chunk_count = (
            self.db.query(KnowledgeChunk)
            .filter(KnowledgeChunk.source_id.in_(source_ids))
            .count()
            if source_ids
            else 0
        )
        failed_jobs = (
            self.db.query(EmbeddingJob)
            .filter(EmbeddingJob.source_id.in_(source_ids), EmbeddingJob.status == "failed")
            .count()
            if source_ids
            else 0
        )
        indexed = len([source for source in sources if source.status == "ready"])
        return {
            "sourceCount": len(sources),
            "indexedSourceCount": indexed,
            "chunkCount": chunk_count,
            "failedJobCount": failed_jobs,
            "coverageRate": round(indexed / len(sources), 4) if sources else 0,
            "vectorBackend": settings.rag_vector_backend,
        }

    def import_file(
        self,
        filename: str,
        data: bytes,
        content_type: str,
        user_id: int,
        workspace_id: int | None = None,
        title: str | None = None,
    ) -> dict:
        if not data:
            raise ValueError("上传文件不能为空")
        if len(data) > settings.knowledge_max_upload_bytes:
            raise ValueError("上传文件超过知识库大小限制")

        suffix = self._file_suffix(filename)
        if suffix not in SUPPORTED_IMPORT_TYPES:
            raise ValueError("仅支持 PDF、DOCX、Markdown、TXT 文件")

        workspace = (
            PlatformService(self.db).ensure_personal_workspace(user_id)
            if workspace_id is None
            else PlatformService(self.db).require_workspace_role(
                workspace_id,
                user_id,
                {"owner", "admin", "member"},
            )
        )
        pages = self._extract_file_pages(filename, data)
        normalized_title = (title or filename or "Uploaded source").strip()[:240]
        digest = self._hash("\n\n".join(page["content"] for page in pages))

        source = KnowledgeSource(
            source_type=self._source_type_from_suffix(suffix),
            title=normalized_title,
            uri=f"upload://{filename}",
            owner_id=user_id,
            workspace_id=workspace.id,
            status="pending",
            content_hash=digest,
            metadata_json=json.dumps(
                {
                    "filename": filename,
                    "contentType": content_type,
                    "bytes": len(data),
                },
                ensure_ascii=False,
            ),
            permission_snapshot_json=json.dumps(
                {"workspaceId": workspace.id, "ownerId": user_id},
                ensure_ascii=False,
            ),
        )
        self.db.add(source)
        self.db.flush()
        job = self._create_job(source, user_id)
        self.db.commit()
        self._process_source_job(source, job, pages)
        return self._source_to_dict(source)

    def reindex_source(self, source_id: int, user_id: int) -> dict:
        source = self._require_source_access(source_id, user_id, write=True)
        if source.document_id is not None:
            document = self.db.query(Document).filter(Document.id == source.document_id).first()
            if not document or document.deleted_at is not None:
                raise ValueError("关联文档不存在或已删除")
            self.ensure_document_index(document, requested_by=user_id)
        else:
            source.status = "ready" if self._source_chunk_count(source.id) else "failed"
            source.updated_at = datetime.now()
            self.db.commit()
        return self._source_to_dict(source)

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

    def _accessible_documents(
        self,
        user_id: int,
        document_id: int | None,
        workspace_id: int | None = None,
    ) -> list[Document]:
        platform_filter = PlatformService(self.db).visible_document_filter(user_id)
        permission_filter = or_(
            Document.creator_id == user_id,
            Document.is_public.is_(True),
            DocumentShare.user_id == user_id,
            platform_filter,
        )
        query = (
            self.db.query(Document)
            .outerjoin(DocumentShare, DocumentShare.document_id == Document.id)
            .filter(permission_filter)
            .filter(Document.deleted_at.is_(None))
            .distinct()
        )
        if document_id is not None:
            query = query.filter(Document.id == document_id)
        if workspace_id is not None:
            PlatformService(self.db).require_workspace_access(workspace_id, user_id)
            query = query.filter(Document.workspace_id == workspace_id)
        return query.order_by(Document.updated_at.desc(), Document.id.desc()).all()

    def _accessible_sources(
        self,
        user_id: int,
        document_id: int | None = None,
        workspace_id: int | None = None,
    ) -> list[KnowledgeSource]:
        documents = self._accessible_documents(user_id, document_id, workspace_id)
        document_ids = [doc.id for doc in documents]
        workspace_ids = [
            row.workspace_id
            for row in self.db.query(WorkspaceMember.workspace_id)
            .filter(WorkspaceMember.user_id == user_id)
            .all()
        ]
        filters = [
            KnowledgeSource.owner_id == user_id,
            KnowledgeSource.document_id.in_(document_ids or [-1]),
            KnowledgeSource.workspace_id.in_(workspace_ids or [-1]),
        ]
        query = self.db.query(KnowledgeSource).filter(or_(*filters))
        if document_id is not None:
            query = query.filter(KnowledgeSource.document_id == document_id)
        if workspace_id is not None:
            PlatformService(self.db).require_workspace_access(workspace_id, user_id)
            query = query.filter(KnowledgeSource.workspace_id == workspace_id)
        return query.order_by(KnowledgeSource.updated_at.desc(), KnowledgeSource.id.desc()).all()

    def _require_source_access(
        self,
        source_id: int,
        user_id: int,
        write: bool = False,
    ) -> KnowledgeSource:
        source = self.db.query(KnowledgeSource).filter(KnowledgeSource.id == source_id).first()
        if not source:
            raise ValueError("知识源不存在")
        if source.document_id is not None:
            document = self.db.query(Document).filter(Document.id == source.document_id).first()
            if not document or document.deleted_at is not None:
                raise ValueError("关联文档不存在或已删除")
            permission = PlatformService(self.db).document_permission(document, user_id)
            if permission in (("owner", "manage", "edit") if write else ("owner", "manage", "edit", "comment", "view")):
                return source
        if source.owner_id == user_id:
            return source
        if source.workspace_id is not None:
            roles = {"owner", "admin", "member"} if write else {"owner", "admin", "member", "viewer"}
            PlatformService(self.db).require_workspace_role(source.workspace_id, user_id, roles)
            return source
        raise ValueError("No permission to access this knowledge source")

    def _index_document_source(self, document: Document, digest: str, requested_by: int) -> None:
        source = (
            self.db.query(KnowledgeSource)
            .filter(KnowledgeSource.document_id == document.id)
            .first()
        )
        if source and source.content_hash == digest and source.status == "ready":
            return
        if not source:
            source = KnowledgeSource(
                source_type="document",
                title=document.title or "Untitled Document",
                uri=f"document://{document.id}",
                owner_id=document.creator_id,
                workspace_id=document.workspace_id,
                document_id=document.id,
            )
            self.db.add(source)
            self.db.flush()

        source.title = document.title or "Untitled Document"
        source.workspace_id = document.workspace_id
        source.status = "indexing"
        source.content_hash = digest
        source.version = (source.version or 1) + 1
        source.metadata_json = json.dumps(
            {
                "revision": document.revision,
                "contentFormat": document.content_format,
            },
            ensure_ascii=False,
        )
        source.permission_snapshot_json = json.dumps(
            {
                "documentId": document.id,
                "workspaceId": document.workspace_id,
                "ownerId": document.creator_id,
                "isPublic": document.is_public,
            },
            ensure_ascii=False,
        )
        job = self._create_job(source, requested_by)
        self.db.commit()
        pages = [{"content": document.content or "", "pageNumber": None, "locationLabel": "正文"}]
        self._process_source_job(source, job, pages)

    def _process_source_job(self, source: KnowledgeSource, job: EmbeddingJob, pages: list[dict]) -> None:
        job.status = "running"
        job.started_at = datetime.now()
        source.status = "indexing"
        self.db.commit()
        try:
            chunks = self._chunks_from_pages(pages)
            self.db.query(KnowledgeChunk).filter(KnowledgeChunk.source_id == source.id).delete()
            self.db.add_all(
                [
                    KnowledgeChunk(
                        source_id=source.id,
                        source_type=source.source_type,
                        document_id=source.document_id,
                        workspace_id=source.workspace_id,
                        chunk_index=index,
                        content=chunk["content"],
                        content_hash=self._hash(chunk["content"]),
                        embedding_json=json.dumps(self._embed(chunk["content"])),
                        lexical_tokens=" ".join(self.tokenize(chunk["content"])),
                        page_number=chunk.get("pageNumber"),
                        location_label=chunk.get("locationLabel") or f"片段 {index + 1}",
                        source_version=source.version,
                        permission_snapshot_json=source.permission_snapshot_json,
                    )
                    for index, chunk in enumerate(chunks)
                    if chunk["content"].strip()
                ]
            )
            source.status = "ready"
            source.indexed_at = datetime.now()
            source.updated_at = datetime.now()
            job.status = "completed"
            job.completed_at = datetime.now()
            job.error = ""
        except Exception as exc:
            source.status = "failed"
            job.status = "failed"
            job.completed_at = datetime.now()
            job.retry_count += 1
            job.error = str(exc)[:2000]
        self.db.commit()
        self.db.refresh(source)

    def _create_job(self, source: KnowledgeSource, requested_by: int) -> EmbeddingJob:
        job = EmbeddingJob(
            source_id=source.id,
            document_id=source.document_id,
            workspace_id=source.workspace_id,
            requested_by=requested_by,
            status="pending",
        )
        self.db.add(job)
        self.db.flush()
        return job

    def _chunks_from_pages(self, pages: list[dict]) -> list[dict]:
        chunks: list[dict] = []
        for page in pages:
            for index, content in enumerate(self.split_text(page.get("content") or "")):
                chunks.append(
                    {
                        "content": content,
                        "pageNumber": page.get("pageNumber"),
                        "locationLabel": page.get("locationLabel") or (
                            f"第 {page['pageNumber']} 页" if page.get("pageNumber") else f"片段 {index + 1}"
                        ),
                    }
                )
        return chunks

    def _hit_from_chunk(
        self,
        source: KnowledgeSource,
        chunk: KnowledgeChunk,
        score: float,
        matched: list[str],
    ) -> SearchHit:
        return SearchHit(
            document_id=chunk.document_id or 0,
            title=source.title or "Untitled Source",
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            score=score,
            matched_terms=matched,
            source_id=source.id,
            source_type=source.source_type,
            workspace_id=chunk.workspace_id,
            page_number=chunk.page_number,
            location_label=chunk.location_label,
        )

    def _source_to_dict(self, source: KnowledgeSource) -> dict:
        chunk_count = self._source_chunk_count(source.id)
        return {
            "id": source.id,
            "sourceType": source.source_type,
            "title": source.title,
            "uri": source.uri,
            "ownerId": source.owner_id,
            "workspaceId": source.workspace_id,
            "documentId": source.document_id,
            "status": source.status,
            "version": source.version,
            "chunkCount": chunk_count,
            "metadata": self._loads_json(source.metadata_json),
            "indexedAt": source.indexed_at.isoformat() if source.indexed_at else None,
            "createdAt": source.created_at.isoformat() if source.created_at else None,
            "updatedAt": source.updated_at.isoformat() if source.updated_at else None,
        }

    @staticmethod
    def _job_to_dict(job: EmbeddingJob) -> dict:
        return {
            "id": job.id,
            "sourceId": job.source_id,
            "documentId": job.document_id,
            "workspaceId": job.workspace_id,
            "requestedBy": job.requested_by,
            "status": job.status,
            "error": job.error,
            "retryCount": job.retry_count,
            "startedAt": job.started_at.isoformat() if job.started_at else None,
            "completedAt": job.completed_at.isoformat() if job.completed_at else None,
            "createdAt": job.created_at.isoformat() if job.created_at else None,
        }

    def _source_chunk_count(self, source_id: int) -> int:
        return self.db.query(KnowledgeChunk).filter(KnowledgeChunk.source_id == source_id).count()

    @staticmethod
    def _rerank_bonus(title: str, content: str, query_phrase: str, matched: list[str]) -> float:
        title_text = RAGService._normalize(title)
        content_text = RAGService._normalize(content)
        phrase = 0.08 if query_phrase and query_phrase in content_text else 0.0
        title = 0.08 if any(term in title_text for term in matched) else 0.0
        return phrase + title

    @staticmethod
    def _embed(text: str) -> list[float]:
        vector = [0.0] * LOCAL_VECTOR_DIMENSIONS
        for token in RAGService.tokenize(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:2], "big") % LOCAL_VECTOR_DIMENSIONS
            sign = 1.0 if digest[2] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [round(value / norm, 6) for value in vector]

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        if not left or not right:
            return 0.0
        length = min(len(left), len(right))
        score = sum(left[index] * right[index] for index in range(length))
        return max(0.0, min(1.0, (score + 1.0) / 2.0))

    @staticmethod
    def _loads_vector(raw: str) -> list[float]:
        try:
            value = json.loads(raw or "[]")
            return value if isinstance(value, list) else []
        except json.JSONDecodeError:
            return []

    @staticmethod
    def _loads_json(raw: str) -> dict:
        try:
            value = json.loads(raw or "{}")
            return value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _file_suffix(filename: str) -> str:
        match = re.search(r"(\.[A-Za-z0-9]+)$", filename or "")
        return match.group(1).lower() if match else ""

    @staticmethod
    def _source_type_from_suffix(suffix: str) -> str:
        return {
            ".pdf": "upload_pdf",
            ".docx": "upload_docx",
            ".md": "upload_markdown",
            ".markdown": "upload_markdown",
            ".txt": "upload_text",
        }.get(suffix, "upload")

    def _extract_file_pages(self, filename: str, data: bytes) -> list[dict]:
        suffix = self._file_suffix(filename)
        if suffix == ".docx":
            return [{"content": self._extract_docx_text(data), "pageNumber": None, "locationLabel": "DOCX"}]
        if suffix == ".pdf":
            return self._extract_pdf_pages(data)
        text = self._decode_text(data)
        return [{"content": text, "pageNumber": None, "locationLabel": "全文"}]

    @staticmethod
    def _decode_text(data: bytes) -> str:
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="ignore")

    @staticmethod
    def _extract_docx_text(data: bytes) -> str:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            xml = archive.read("word/document.xml").decode("utf-8", errors="ignore")
        texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", xml)
        return "\n".join(re.sub(r"<[^>]+>", "", item) for item in texts)

    @staticmethod
    def _extract_pdf_pages(data: bytes) -> list[dict]:
        try:
            from pypdf import PdfReader
        except Exception as exc:
            raise ValueError("PDF 解析依赖不可用，请安装 pypdf") from exc

        reader = PdfReader(BytesIO(data))
        pages = []
        for index, page in enumerate(reader.pages, start=1):
            pages.append(
                {
                    "content": page.extract_text() or "",
                    "pageNumber": index,
                    "locationLabel": f"第 {index} 页",
                }
            )
        return pages

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"\s+", " ", (value or "").strip().lower())

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256((value or "").encode("utf-8")).hexdigest()
