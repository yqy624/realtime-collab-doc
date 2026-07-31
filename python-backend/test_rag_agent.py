import unittest

from app.services.agent_graph import KnowledgeAgent
from app.services.rag_service import RAGService


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


if __name__ == "__main__":
    unittest.main()
