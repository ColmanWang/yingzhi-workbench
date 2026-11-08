import unittest
from unittest.mock import patch, MagicMock
from douyin_favorites_knowledge.workbench.url_parser import (
    extract_douyin_url,
    resolve_aweme_id,
)


class UrlParserTests(unittest.TestCase):
    def test_extract_douyin_url_from_share_text(self):
        text = "8.88 复制打开抖音，看看【张三的作品】 https://v.douyin.com/iANabcd/ 精彩不容错过"
        extracted = extract_douyin_url(text)
        self.assertEqual(extracted, "https://v.douyin.com/iANabcd")

    def test_extract_douyin_url_direct_link(self):
        url = "https://www.douyin.com/video/7123456789012345678"
        self.assertEqual(extract_douyin_url(url), url)

    def test_extract_douyin_url_raw_id(self):
        aweme_id = "7123456789012345678"
        self.assertEqual(
            extract_douyin_url(aweme_id),
            "https://www.douyin.com/video/7123456789012345678",
        )

    def test_extract_douyin_url_invalid(self):
        self.assertIsNone(extract_douyin_url("这是一段没有任何链接的普通文本"))
        self.assertIsNone(extract_douyin_url("https://www.bilibili.com/video/BV12345678"))
        self.assertIsNone(extract_douyin_url(None))

    def test_resolve_aweme_id_direct_video(self):
        url = "https://www.douyin.com/video/7123456789012345678"
        aweme_id, canonical = resolve_aweme_id(url)
        self.assertEqual(aweme_id, "7123456789012345678")
        self.assertEqual(canonical, "https://www.douyin.com/video/7123456789012345678")

    def test_resolve_aweme_id_direct_note(self):
        url = "https://www.douyin.com/note/7123456789012345678"
        aweme_id, canonical = resolve_aweme_id(url)
        self.assertEqual(aweme_id, "7123456789012345678")
        self.assertEqual(canonical, "https://www.douyin.com/video/7123456789012345678")

    def test_resolve_aweme_id_query_modal_id(self):
        url = "https://www.douyin.com/discover?modal_id=7123456789012345678"
        aweme_id, canonical = resolve_aweme_id(url)
        self.assertEqual(aweme_id, "7123456789012345678")
        self.assertEqual(canonical, "https://www.douyin.com/video/7123456789012345678")

    @patch("urllib.request.urlopen")
    def test_resolve_aweme_id_short_link_redirect(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.geturl.return_value = "https://www.douyin.com/video/7123456789012345678?previous_page=app_code"
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        share_text = "4.12 复制打开抖音，看看【李四的作品】 https://v.douyin.com/kXYZ123/ 复制此链接"
        aweme_id, canonical = resolve_aweme_id(share_text)
        self.assertEqual(aweme_id, "7123456789012345678")
        self.assertEqual(canonical, "https://www.douyin.com/video/7123456789012345678")

    def test_resolve_aweme_id_not_found(self):
        with self.assertRaises(ValueError):
            resolve_aweme_id("纯文字，不包含任何链接")


if __name__ == "__main__":
    unittest.main()
