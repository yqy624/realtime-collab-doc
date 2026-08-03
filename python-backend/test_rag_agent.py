import unittest

from langchain_core.output_parsers import StrOutputParser

from app.services.agent_chain import KnowledgeAgent
from app.services.rag_service import RAGService
from app.services.rag_service import SearchHit


class FakeRAG:
    def __init__(self, hits):
        self.hits = hits

    def search(self, *args, **kwargs):
        return self.hits


class FakeLLM:
    model = "fake-model"

    def generate(self, prompt):
        return "基于参考资料的回答 [Reference 1]", 7


class RAGServiceTests(unittest.TestCase):
    def test_split_text_uses_bounded_chunks(self):
        chunks = RAGService.split_text("a" * 2200)
        self.assertGreater(len(chunks), 2)
        self.assertTrue(all(len(chunk) <= 900 for chunk in chunks))

    def test_tokenize_supports_chinese_bigrams_and_english_words(self):
        tokens = RAGService.tokenize("实时协作 Agent")
        self.assertIn("实时", tokens)
        self.assertIn("协作", tokens)
        self.assertIn("agent", tokens)

    def test_score_rewards_a_query_phrase(self):
        score, matched = RAGService._score(
            "实时协作支持多人同时编辑",
            RAGService.tokenize("实时协作"),
            "实时协作",
        )
        self.assertGreaterEqual(score, 0.8)
        self.assertIn("协作", matched)


class AgentRoutingTests(unittest.TestCase):
    def test_agent_refuses_without_evidence(self):
        state = KnowledgeAgent._route_evidence({"hits": []})
        self.assertTrue(state["refusal"])
        self.assertEqual(KnowledgeAgent._route_after_evidence({"hits": []}), "refuse")

    def _build_agent(self, hits):
        agent = KnowledgeAgent.__new__(KnowledgeAgent)
        agent.db = None
        agent.rag = FakeRAG(hits)
        agent.llm = FakeLLM()
        agent.output_parser = StrOutputParser()
        agent.chain = agent._build_chain()
        return agent

    def test_langchain_chain_generates_grounded_answer(self):
        agent = self._build_agent(
            [SearchHit(1, "Test document", 0, "Permission is required.", 0.9, ["permission"])]
        )

        result = agent.run("How is permission handled?", 1)

        self.assertFalse(result["refusal"])
        self.assertEqual(result["model"], "fake-model")
        self.assertEqual(result["trace"]["orchestration"], "langchain_lcel")
        self.assertEqual(len(result["citations"]), 1)

    def test_langchain_chain_refuses_without_evidence(self):
        result = self._build_agent([]).run("Unknown question", 1)

        self.assertTrue(result["refusal"])
        self.assertEqual(result["model"], "lexical-rag")
        self.assertEqual(result["citations"], [])


if __name__ == "__main__":
    unittest.main()
