import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from douyin_favorites_knowledge.workbench.card_renderer import (
    THEMES,
    validate_card,
    render_card,
    export_card_png,
)


class CardRendererTests(unittest.TestCase):
    def setUp(self):
        self.sample_card = {
            "title": "测试知识卡片标题",
            "author": "测试作者",
            "source_url": "https://www.douyin.com/video/7123456789012345678",
            "summary": "这是测试的核心知识摘要内容，解释了概念与背景。",
            "points": ["核心要点一：理解基础", "核心要点二：实践验证"],
            "actions": ["行动建议一：每天练习", "行动建议二：复盘总结"],
            "synthetic": False,
        }

    def test_validate_card_success(self):
        validated = validate_card(self.sample_card)
        self.assertEqual(validated["title"], "测试知识卡片标题")

    def test_validate_card_rejects_non_douyin_url(self):
        card = dict(self.sample_card, source_url="https://evil.com/video/123")
        with self.assertRaises(ValueError):
            validate_card(card)

    def test_validate_card_rejects_empty_points(self):
        card = dict(self.sample_card, points=[])
        with self.assertRaises(ValueError):
            validate_card(card)

    def test_render_card_all_themes(self):
        for theme_key in ("classic", "minimal", "dark", "xiaohongshu"):
            html = render_card(self.sample_card, theme=theme_key)
            self.assertIn("<!doctype html>", html)
            self.assertIn(self.sample_card["title"], html)
            self.assertIn(self.sample_card["author"], html)
            self.assertIn(self.sample_card["summary"], html)
            self.assertIn(self.sample_card["points"][0], html)
            self.assertIn(self.sample_card["actions"][0], html)
            self.assertIn(self.sample_card["source_url"], html)

    def test_render_card_escapes_xss_attacks(self):
        xss_card = {
            "title": "<script>alert('title')</script>",
            "author": "<b>Hacker</b>",
            "source_url": "https://www.douyin.com/video/7123456789012345678",
            "summary": "尝试注入 <iframe src='javascript:alert(1)'>",
            "points": ["<script>alert('point')</script>"],
            "actions": ["<style>body{display:none}</style>"],
            "synthetic": False,
        }
        html = render_card(xss_card, theme="minimal")
        self.assertNotIn("<script>", html)
        self.assertNotIn("<b>Hacker</b>", html)
        self.assertNotIn("<iframe", html)
        self.assertIn("&lt;script&gt;alert(&#x27;title&#x27;)&lt;/script&gt;", html)
        self.assertIn("&lt;b&gt;Hacker&lt;/b&gt;", html)

    def test_render_card_author_credit_and_synthetic_badge(self):
        card = dict(self.sample_card, synthetic=True)
        html = render_card(card, theme="classic", author_credit="小李")
        self.assertIn("合成演示 · 非真实视频分析", html)
        self.assertIn("由 小李 整理", html)

    @patch("builtins.__import__")
    def test_export_card_png_fallback_when_playwright_missing(self, mock_import):
        mock_import.side_effect = ImportError("playwright not installed")
        res = export_card_png(Path("fake.html"), Path("fake.png"))
        self.assertFalse(res)


if __name__ == "__main__":
    unittest.main()
