import unittest

from cards import render_card, validate_card


def fixture():
    return {
        "title": "如何复习", "author": "示例作者", "source_url": "https://www.douyin.com/video/123",
        "summary": "先回忆，再核对。", "points": ["合上材料回忆", "核对遗漏"],
        "actions": ["今天练习一次"], "synthetic": True,
    }


class CardTests(unittest.TestCase):
    def test_source_and_synthetic_label_are_preserved(self):
        output = render_card(fixture())
        self.assertIn("合成演示", output)
        self.assertIn("https://www.douyin.com/video/123", output)
        self.assertIn("示例作者", output)

    def test_untrusted_text_is_escaped(self):
        card = {**fixture(), "title": '<script>alert("x")</script>'}
        output = render_card(card)
        self.assertNotIn("<script>", output)
        self.assertIn("&lt;script&gt;", output)

    def test_unsafe_source_is_rejected(self):
        for url in ("javascript:alert(1)", "file:///etc/passwd", "https://evil.example/video/1"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_card({**fixture(), "source_url": url})

    def test_invalid_data_fails_clearly(self):
        for changes in ({"title": ""}, {"points": "bad"}, {"actions": [5]}, {"synthetic": "yes"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_card({**fixture(), **changes})

    def test_render_does_not_mutate_input(self):
        card = fixture()
        before = repr(card)
        render_card(card)
        self.assertEqual(before, repr(card))


if __name__ == "__main__":
    unittest.main()
