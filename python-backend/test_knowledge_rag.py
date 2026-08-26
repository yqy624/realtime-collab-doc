import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import Base
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.services.rag_service import RAGService


class KnowledgeRAGTests(unittest.TestCase):
    sequence = 0

    @classmethod
    def setUpClass(cls):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)
        cls.Session = sessionmaker(bind=engine)

    def setUp(self):
        type(self).sequence += 1
        suffix = type(self).sequence
        self.db = self.Session()
        self.owner = User(
            username=f"knowledge-owner-{suffix}",
            email=f"knowledge-owner-{suffix}@example.com",
            password_hash="test",
        )
        self.viewer = User(
            username=f"knowledge-viewer-{suffix}",
            email=f"knowledge-viewer-{suffix}@example.com",
            password_hash="test",
        )
        self.outsider = User(
            username=f"knowledge-outsider-{suffix}",
            email=f"knowledge-outsider-{suffix}@example.com",
            password_hash="test",
        )
        self.db.add_all([self.owner, self.viewer, self.outsider])
        self.db.flush()
        self.workspace = Workspace(
            name=f"Knowledge Space {suffix}",
            description="",
            owner_id=self.owner.id,
        )
        self.db.add(self.workspace)
        self.db.flush()
        self.db.add_all(
            [
                WorkspaceMember(
                    workspace_id=self.workspace.id,
                    user_id=self.owner.id,
                    role="owner",
                ),
                WorkspaceMember(
                    workspace_id=self.workspace.id,
                    user_id=self.viewer.id,
                    role="viewer",
                ),
            ]
        )
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_imported_text_source_is_indexed_with_citation(self):
        result = RAGService(self.db).import_file(
            "handbook.txt",
            "混合 RAG 需要返回 citation 并遵守空间权限。".encode("utf-8"),
            "text/plain",
            self.owner.id,
            workspace_id=self.workspace.id,
        )

        response = RAGService(self.db).search_response(
            "citation 权限",
            self.viewer.id,
            workspace_id=self.workspace.id,
        )

        self.assertEqual(result["status"], "ready")
        self.assertGreater(result["chunkCount"], 0)
        self.assertEqual(response["retrieval"]["type"], "hybrid")
        self.assertEqual(response["retrieval"]["workspaceScope"], self.workspace.id)
        self.assertTrue(response["citations"])
        self.assertEqual(response["citations"][0]["sourceType"], "upload_text")

    def test_outsider_cannot_search_workspace_source(self):
        RAGService(self.db).import_file(
            "secret.md",
            "# 内部资料\n\n只有空间成员可以检索。".encode("utf-8"),
            "text/markdown",
            self.owner.id,
            workspace_id=self.workspace.id,
        )

        response = RAGService(self.db).search_response(
            "内部资料",
            self.outsider.id,
            workspace_id=None,
        )

        self.assertEqual(response["total"], 0)
        self.assertEqual(response["results"], [])

    def test_document_index_refreshes_to_knowledge_chunks(self):
        document = Document(
            title="可信问答设计",
            content="第一版内容强调关键词检索。",
            creator_id=self.owner.id,
            workspace_id=self.workspace.id,
            is_public=False,
            revision=1,
        )
        self.db.add(document)
        self.db.commit()

        service = RAGService(self.db)
        service.ensure_document_index(document, requested_by=self.owner.id)
        document.content = "第二版内容强调向量召回、rerank 和 citation。"
        document.revision = 2
        self.db.commit()
        service.ensure_document_index(document, requested_by=self.owner.id)

        response = service.search_response("rerank citation", self.viewer.id)

        self.assertEqual(response["total"], 1)
        self.assertEqual(response["results"][0]["documentId"], document.id)
        self.assertIn("第二版内容", response["results"][0]["content"])
        self.assertEqual(response["citations"][0]["sourceType"], "document")

    def test_existing_document_chunks_backfill_knowledge_source(self):
        document = Document(
            title="旧索引文档",
            content="旧 document_chunks 也应该回填到知识源。",
            creator_id=self.owner.id,
            workspace_id=self.workspace.id,
            is_public=False,
            revision=1,
        )
        self.db.add(document)
        self.db.flush()
        digest = RAGService._hash(document.content)
        self.db.add(
            DocumentChunk(
                document_id=document.id,
                chunk_index=0,
                content=document.content,
                content_hash=digest,
            )
        )
        self.db.commit()

        response = RAGService(self.db).search_response("回填 知识源", self.viewer.id)

        self.assertEqual(response["total"], 1)
        self.assertEqual(response["citations"][0]["sourceType"], "document")


if __name__ == "__main__":
    unittest.main()
