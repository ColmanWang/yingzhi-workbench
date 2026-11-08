"""Douyin share link parser and aweme_id extractor."""
from __future__ import annotations

import re
import urllib.error
import urllib.request
from urllib.parse import parse_qs, urlsplit

URL_REGEX = re.compile(r"https?://(?:[a-zA-Z0-9_-]+\.)?douyin\.com/[^\s\"'<>，。！？]+")
AWEME_ID_REGEX = re.compile(r"^[0-9]{6,30}$")
VIDEO_PATH_REGEX = re.compile(r"/video/([0-9]{6,30})")
NOTE_PATH_REGEX = re.compile(r"/note/([0-9]{6,30})")


def extract_douyin_url(text: str) -> str | None:
    """Extract first Douyin HTTPS/HTTP URL from clipboard share text."""
    if not isinstance(text, str):
        return None
    cleaned = text.strip()
    match = URL_REGEX.search(cleaned)
    if match:
        url = match.group(0).rstrip("，。！？/ \t\n\r")
        return url
    if AWEME_ID_REGEX.fullmatch(cleaned):
        return f"https://www.douyin.com/video/{cleaned}"
    return None


def resolve_aweme_id(input_text: str, timeout: int = 10) -> tuple[str, str]:
    """Resolve an aweme_id and canonical URL from share text or direct link."""
    url = extract_douyin_url(input_text)
    if not url:
        raise ValueError("未在输入内容中找到有效的抖音链接或视频 ID")

    # Fast path: already direct video URL
    v_match = VIDEO_PATH_REGEX.search(url) or NOTE_PATH_REGEX.search(url)
    if v_match:
        aweme_id = v_match.group(1)
        canonical_url = f"https://www.douyin.com/video/{aweme_id}"
        return aweme_id, canonical_url

    # Check query params (e.g. modal_id)
    parsed = urlsplit(url)
    qs = parse_qs(parsed.query)
    for q_key in ("modal_id", "aweme_id"):
        val = qs.get(q_key, [""])[0]
        if AWEME_ID_REGEX.fullmatch(val):
            return val, f"https://www.douyin.com/video/{val}"

    # Follow redirect for short links (e.g. v.douyin.com)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            final_url = resp.geturl()
            match = VIDEO_PATH_REGEX.search(final_url) or NOTE_PATH_REGEX.search(final_url)
            if match:
                aweme_id = match.group(1)
                return aweme_id, f"https://www.douyin.com/video/{aweme_id}"
            qs = parse_qs(urlsplit(final_url).query)
            for q_key in ("modal_id", "aweme_id"):
                val = qs.get(q_key, [""])[0]
                if AWEME_ID_REGEX.fullmatch(val):
                    return val, f"https://www.douyin.com/video/{val}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ValueError(f"解析短链接重定向失败: {exc}") from exc

    raise ValueError("未能从该链接解析出具体的抖音视频 ID")
