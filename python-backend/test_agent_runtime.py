import json
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import Base
from app.models.document import Document
from app.models.user import User
from app.services.agent_runtime import AgentPlanner, AgentRuntime, AgentToolRegistry


class FakeLLM:
    model = "fake-agent-model"

    def generate(self, prompt: str):
        if "You are an Agent planner" in prompt:
            return "planner unavailable", 1
        return (
            json.dumps(
                {
                    "answer": "这是基于工具结果生成的回答。",
                    "proposedContent": "更新后的文档内容",
                },
                ensure_ascii=False,
            ),
            2,
        )


class AgentRuntimeTests(unittest.TestCase):
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
        self.db = self.Session()
        self.user = User(
            username=f"agent-user-{self.sequence}",
            email=f"agent-{self.sequence}@example.com",
            password_hash="test",
        )
        self.db.add(self.user)
        self.db.flush()
        self.document = Document(
            title="Agent Test",
            content="这是一个实时协作文档，包含工具调用和知识库内容。",
            creator_id=self.user.id,
            is_public=False,
            revision=0,
        )
        self.db.add(self.document)
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_run_persists_plan_tools_trace_and_memory(self):
        result = AgentRuntime(self.db, llm=FakeLLM()).start(
            "总结当前文档并指出风险",
            self.user.id,
            self.document.id,
        )

        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["result"])
        self.assertGreaterEqual(len(result["plan"]), 4)
        self.assertTrue(any(step["tool"] == "search_knowledge" for step in result["plan"]))
        self.assertTrue(result["trace"])
        self.assertTrue(result["memories"])

    def test_live_news_plan_includes_web_search_and_write_review(self):
        plan = AgentPlanner(FakeLLM()).plan(
            "查询今天的实时新闻并写入文档",
            self.document.id,
        )

        tools = [step["tool"] for step in plan]
        self.assertIn("web_search", tools)
        self.assertLess(tools.index("web_search"), tools.index("model_generate"))
        self.assertIn("generate_diff", tools)
        self.assertIn("apply_document_content", tools)

    def test_write_plan_waits_for_approval_then_executes(self):
        runtime = AgentRuntime(self.db, llm=FakeLLM())
        pending = runtime.start(
            "修改当前文档，重写成更清晰的版本",
            self.user.id,
            self.document.id,
        )

        self.assertEqual(pending["status"], "awaiting_approval")
        self.assertEqual(pending["pendingApproval"]["tool"], "apply_document_content")

        completed = runtime.approve(pending["runId"], self.user.id, True)

        self.assertEqual(completed["status"], "completed")
        self.assertEqual(self.document.content, "更新后的文档内容")
        self.assertGreater(self.document.revision, 0)

    def test_tool_specs_include_web_search(self):
        specs = AgentToolRegistry.specs()
        names = {item["name"] for item in specs}

        self.assertIn("web_search", names)
        web_search = next(item for item in specs if item["name"] == "web_search")
        self.assertTrue(web_search["readOnly"])
        self.assertFalse(web_search["requiresApproval"])


if __name__ == "__main__":
    unittest.main()
