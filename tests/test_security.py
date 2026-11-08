import unittest

from douyin_favorites_knowledge.security import safe_error_message, BLOCKED_PATTERNS


class SecurityTests(unittest.TestCase):
    def test_masks_openai_and_deepseek_keys(self):
        msg = safe_error_message(Exception("Failed request with key sk-1234567890abcdef1234567890"))
        self.assertNotIn("1234567890abcdef", msg)
        self.assertIn("[REDACTED]", msg)

    def test_masks_bearer_tokens(self):
        msg = safe_error_message(Exception("Unauthorized: Bearer eyJhbGciOiJIUzI1NiJ9.test.token"))
        self.assertNotIn("eyJhbGciOiJIUzI1NiJ9", msg)
        self.assertIn("[REDACTED]", msg)

    def test_masks_sensitive_cookies(self):
        msg = safe_error_message(Exception("Network error while sending sessionid=abc123456789; other=ok"))
        self.assertNotIn("sessionid=abc123456789", msg)
        self.assertIn("[REDACTED]", msg)

    def test_masks_private_paths(self):
        msg = safe_error_message(Exception("File missing at /Users/someone/secret/notes.db"))
        self.assertNotIn("/Users/someone", msg)
        self.assertIn("[PRIVATE_PATH]", msg)


if __name__ == "__main__":
    unittest.main()
