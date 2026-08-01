import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import Base
from app.models.document import Document
from app.models.document_share import DocumentShare
from app.models.document_snapshot import DocumentSnapshot
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.services.agent_runtime import AgentPlanner
from app.services.document_service import DocumentService


class SecurityRegressionTests(unittest.TestCase):
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
            username=f"security-owner-{suffix}",
            email=f"security-owner-{suffix}@example.com",
            password_hash="test",
        )
        self.viewer = User(
            username=f"security-viewer-{suffix}",
            email=f"security-viewer-{suffix}@example.com",
            password_hash="test",
        )
        self.db.add_all([self.owner, self.viewer])
        self.db.flush()
        self.document = Document(
            title="Private document",
            content="original",
            creator_id=self.owner.id,
            is_public=False,
            revision=1,
        )
        self.other_document = Document(
            title="Other document",
            content="other",
            creator_id=self.owner.id,
            is_public=False,
            revision=2,
        )
        self.db.add_all([self.document, self.other_document])
        self.db.flush()
        self.db.add(
            DocumentShare(
                document_id=self.document.id,
                user_id=self.viewer.id,
                permission="view",
            )
        )
        self.snapshot = DocumentSnapshot(
            document_id=self.other_document.id,
            title=self.other_document.title,
            content=self.other_document.content,
            revision=self.other_document.revision,
            user_id=self.owner.id,
        )
        self.db.add(self.snapshot)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_viewer_cannot_save_document(self):
        service = DocumentService(self.db)

        with self.assertRaises(ValueError):
            service.save_snapshot(
                self.document.id,
                {"content": "tampered"},
                self.viewer.id,
            )

        self.db.refresh(self.document)
        self.assertEqual(self.document.content, "original")

    def test_document_dto_reports_viewer_permission(self):
        result = DocumentService(self.db).get_document(
            self.document.id,
            self.viewer.id,
        )

        self.assertEqual(result["permission"], "view")

    def test_restore_rejects_snapshot_from_another_document(self):
        with self.assertRaises(ValueError):
            DocumentService(self.db).restore_snapshot(
                self.snapshot.id,
                self.document.id,
                self.owner.id,
            )

    def test_edit_plan_orders_diff_before_apply(self):
        plan = AgentPlanner(None)._normalize(
            [
                {
                    "id": "model",
                    "tool": "model_generate",
                    "args": {},
                    "reason": "",
                },
                {
                    "id": "apply-first",
                    "tool": "apply_document_content",
                    "args": {"content": "$model.proposedContent"},
                    "reason": "",
                },
            ],
            "rewrite this document",
            self.document.id,
        )
        tools = [step["tool"] for step in plan]

        self.assertLess(
            tools.index("generate_diff"),
            tools.index("apply_document_content"),
        )
        self.assertEqual(tools[-1], "remember")


if __name__ == "__main__":
    unittest.main()
