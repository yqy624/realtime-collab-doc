import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import Base
from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.document_share import DocumentShare
from app.models.document_snapshot import DocumentSnapshot
from app.models.document_chunk import DocumentChunk
from app.models.folder import Folder
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.services.agent_runtime import AgentPlanner
from app.services.document_service import DocumentService
from app.services.platform_service import PlatformService


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

    def test_viewer_cannot_persist_document(self):
        service = DocumentService(self.db)

        with self.assertRaises(ValueError):
            service.persist_document(
                self.document.id,
                {"content": "tampered"},
                self.viewer.id,
            )

        self.db.refresh(self.document)
        self.assertEqual(self.document.content, "original")

    def test_editor_can_persist_document_without_snapshot(self):
        share = self.db.query(DocumentShare).filter(
            DocumentShare.document_id == self.document.id,
            DocumentShare.user_id == self.viewer.id,
        ).first()
        share.permission = "edit"
        self.db.commit()

        with patch(
            "app.services.document_service.RAGService.ensure_document_index",
            side_effect=RuntimeError("index unavailable"),
        ):
            result = DocumentService(self.db).persist_document(
                self.document.id,
                {"content": "saved draft"},
                self.viewer.id,
            )

        snapshot_count = self.db.query(DocumentSnapshot).filter(
            DocumentSnapshot.document_id == self.document.id,
        ).count()
        self.assertEqual(result["content"], "saved draft")
        self.assertEqual(snapshot_count, 0)

    def test_direct_edit_share_overrides_workspace_view(self):
        workspace = Workspace(name="Mixed permission space", description="", owner_id=self.owner.id)
        self.db.add(workspace)
        self.db.flush()
        self.db.add_all([
            WorkspaceMember(workspace_id=workspace.id, user_id=self.owner.id, role="owner"),
            WorkspaceMember(workspace_id=workspace.id, user_id=self.viewer.id, role="viewer"),
        ])
        share = self.db.query(DocumentShare).filter(
            DocumentShare.document_id == self.document.id,
            DocumentShare.user_id == self.viewer.id,
        ).first()
        share.permission = "edit"
        self.document.workspace_id = workspace.id
        self.db.commit()

        result = DocumentService(self.db).persist_document(
            self.document.id,
            {"content": "direct edit wins"},
            self.viewer.id,
        )

        self.assertEqual(result["permission"], "edit")
        self.assertEqual(result["content"], "direct edit wins")

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

    def test_workspace_member_can_see_workspace_document(self):
        service = PlatformService(self.db)
        workspace = Workspace(
            name="Team space",
            description="",
            owner_id=self.owner.id,
        )
        self.db.add(workspace)
        self.db.flush()
        self.db.add_all([
            WorkspaceMember(workspace_id=workspace.id, user_id=self.owner.id, role="owner"),
            WorkspaceMember(workspace_id=workspace.id, user_id=self.viewer.id, role="member"),
        ])
        self.document.workspace_id = workspace.id
        self.db.commit()

        docs = DocumentService(self.db).get_documents_for_user(
            self.viewer.id,
            workspace_id=workspace.id,
        )

        self.assertIn(self.document.id, [item["id"] for item in docs])
        self.assertEqual(service.document_permission(self.document, self.viewer.id), "edit")

    def test_workspace_viewer_cannot_create_document(self):
        workspace = Workspace(name="Readonly space", description="", owner_id=self.owner.id)
        self.db.add(workspace)
        self.db.flush()
        self.db.add_all([
            WorkspaceMember(workspace_id=workspace.id, user_id=self.owner.id, role="owner"),
            WorkspaceMember(workspace_id=workspace.id, user_id=self.viewer.id, role="viewer"),
        ])
        self.db.commit()

        with self.assertRaises(ValueError):
            DocumentService(self.db).create_document(
                "Blocked",
                "",
                False,
                self.viewer.id,
                workspace_id=workspace.id,
            )

    def test_workspace_folder_validates_workspace_boundary(self):
        workspace = Workspace(name="Folder space", description="", owner_id=self.owner.id)
        other_workspace = Workspace(name="Other space", description="", owner_id=self.owner.id)
        self.db.add_all([workspace, other_workspace])
        self.db.flush()
        self.db.add_all([
            WorkspaceMember(workspace_id=workspace.id, user_id=self.owner.id, role="owner"),
            WorkspaceMember(workspace_id=other_workspace.id, user_id=self.owner.id, role="owner"),
        ])
        folder = Folder(workspace_id=other_workspace.id, name="Other folder", creator_id=self.owner.id)
        self.db.add(folder)
        self.db.commit()

        with self.assertRaises(ValueError):
            DocumentService(self.db).create_document(
                "Wrong folder",
                "",
                False,
                self.owner.id,
                workspace_id=workspace.id,
                folder_id=folder.id,
            )

    def test_soft_delete_moves_document_to_trash(self):
        service = DocumentService(self.db)

        service.delete_document(self.document.id, self.owner.id)

        docs = service.get_documents_for_user(self.owner.id)
        trash = service.get_deleted_documents_for_user(self.owner.id)

        self.assertNotIn(self.document.id, [item["id"] for item in docs])
        self.assertIn(self.document.id, [item["id"] for item in trash])
        self.assertIsNotNone(
            self.db.query(AuditLog)
            .filter(AuditLog.action == "document.soft_delete")
            .first()
        )

    def test_restore_deleted_document_returns_to_normal_list(self):
        service = DocumentService(self.db)
        service.delete_document(self.document.id, self.owner.id)

        restored = service.restore_deleted_document(self.document.id, self.owner.id)
        docs = service.get_documents_for_user(self.owner.id)

        self.assertIsNone(restored["deletedAt"])
        self.assertIn(self.document.id, [item["id"] for item in docs])
        self.assertIsNotNone(
            self.db.query(AuditLog)
            .filter(AuditLog.action == "document.restore")
            .first()
        )

    def test_deleted_document_is_not_accessible(self):
        service = DocumentService(self.db)
        service.delete_document(self.document.id, self.owner.id)

        with self.assertRaises(ValueError):
            service.get_document(self.document.id, self.owner.id)

    def test_deleted_document_is_not_accessible_by_share_token(self):
        service = DocumentService(self.db)
        self.document.share_token = "deleted-share-token"
        self.db.commit()

        service.delete_document(self.document.id, self.owner.id)

        with self.assertRaises(ValueError):
            service.access_by_token("deleted-share-token", self.viewer.id)

    def test_trash_only_lists_manageable_deleted_documents(self):
        service = DocumentService(self.db)
        self.document.is_public = True
        self.db.commit()

        service.delete_document(self.document.id, self.owner.id)
        viewer_trash = service.get_deleted_documents_for_user(self.viewer.id)

        self.assertNotIn(self.document.id, [item["id"] for item in viewer_trash])

    def test_workspace_admin_can_read_workspace_audit_logs(self):
        platform = PlatformService(self.db)
        workspace = Workspace(
            name="Governance space",
            description="",
            owner_id=self.owner.id,
        )
        self.db.add(workspace)
        self.db.flush()
        self.db.add_all([
            WorkspaceMember(workspace_id=workspace.id, user_id=self.owner.id, role="owner"),
            WorkspaceMember(workspace_id=workspace.id, user_id=self.viewer.id, role="admin"),
        ])
        self.db.commit()

        platform.create_folder(workspace.id, self.viewer.id, "Audit folder")
        from app.services.audit_service import AuditService

        logs = AuditService(self.db).list_for_workspace(workspace.id)

        self.assertIn("folder.create", [item["action"] for item in logs])


if __name__ == "__main__":
    unittest.main()
