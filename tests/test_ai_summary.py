import unittest
from unittest.mock import patch, MagicMock
from douyin_favorites_knowledge.ai_summary import (
    clean_model_output,
    sanitize_card_data,
    summarize_item,
    check_llm_connection,
)


class AiSummaryTests(unittest.TestCase):
    def test_clean_model_output_with_code_block(self):
        raw = """```json
{"title": "测试标题", "summary": "测试摘要"}
```"""
        self.assertEqual(clean_model_output(raw), '{"title": "测试标题", "summary": "测试摘要"}')

    def test_clean_model_output_with_surrounding_text(self):
        raw = """这是前缀文本
{"title": "测试标题", "summary": "测试摘要"}
这是后缀说明"""
        self.assertEqual(clean_model_output(raw), '{"title": "测试标题", "summary": "测试摘要"}')

    def test_sanitize_card_data_validates_and_defaults(self):
        fallback = {
            "id": "collection-12345678",
            "title": "回退标题",
            "author": "回退作者",
            "source_url": "https://www.douyin.com/video/12345678",
        }
        raw = {
            "title": "大模型给出的好标题",
            "summary": "详细摘要内容",
            "points": ["要点一", "要点二"],
            "actions": ["行动一"],
        }
        sanitized = sanitize_card_data(raw, fallback)
        self.assertEqual(sanitized["title"], "大模型给出的好标题")
        self.assertEqual(sanitized["author"], "回退作者")
        self.assertEqual(sanitized["source_url"], "https://www.douyin.com/video/12345678")
        self.assertEqual(sanitized["summary"], "详细摘要内容")
        self.assertEqual(sanitized["points"], ["要点一", "要点二"])
        self.assertEqual(sanitized["actions"], ["行动一"])
        self.assertFalse(sanitized["synthetic"])

    def test_sanitize_card_data_enforces_safe_douyin_url(self):
        fallback = {
            "id": "collection-12345678",
            "title": "标题",
            "author": "作者",
            "source_url": "https://www.douyin.com/video/12345678",
        }
        raw = {
            "source_url": "https://evil.com/phishing",
            "summary": "内容",
            "points": ["点1"],
            "actions": ["行1"],
        }
        sanitized = sanitize_card_data(raw, fallback)
        # Should reject evil.com and fall back to douyin.com
        self.assertEqual(sanitized["source_url"], "https://www.douyin.com")

    @patch("douyin_favorites_knowledge.ai_summary.call_llm")
    def test_summarize_item_end_to_end(self, mock_call):
        mock_call.return_value = """```json
{
  "title": "视频提炼核心",
  "author": "原作者",
  "source_url": "https://www.douyin.com/video/88888888",
  "summary": "这是摘要",
  "points": ["要点1", "要点2"],
  "actions": ["整理者建议：行动1"]
}
```"""
        item = {
            "id": "like-88888888",
            "title": "原视频标题",
            "author": "原作者",
            "source_url": "https://www.douyin.com/video/88888888",
            "transcript": "这里是一段很长的逐字稿文字...",
        }
        res = summarize_item(item, api_key="sk-test")
        self.assertEqual(res["title"], "视频提炼核心")
        self.assertEqual(res["points"], ["要点1", "要点2"])
        self.assertFalse(res["synthetic"])

    @patch("douyin_favorites_knowledge.ai_summary.call_llm")
    def test_check_llm_connection_success(self, mock_call):
        mock_call.return_value = "OK"
        res = check_llm_connection("http://localhost:11434", "", "llama3")
        self.assertTrue(res["ok"])


if __name__ == "__main__":
    unittest.main()
