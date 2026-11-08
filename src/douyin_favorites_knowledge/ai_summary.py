"""AI summary and structured knowledge extraction for Douyin cards."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlsplit

from .security import safe_error_message

DEFAULT_TIMEOUT = 60
DEFAULT_ENDPOINT = "https://api.siliconflow.cn/v1/chat/completions"
DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"

SYSTEM_PROMPT = """你是一个专业的视频知识提炼专家。你的任务是根据视频信息和逐字稿（或图文画面文案），提取出结构清晰、言之有物的知识卡片内容。

你必须严格以合法的 JSON 格式返回，不要包含任何额外的问候、解释或前缀说明。
返回的 JSON 必须包含以下字段：
1. "title": 标题（精炼有力，概括核心主题，不超过 50 个汉字）。
2. "author": 原作者姓名或账号名称（直接沿用提供的值）。
3. "source_url": 抖音来源链接（直接沿用提供的值）。
4. "summary": 核心摘要（概括视频的核心主旨与背景，严谨客观，100-300字）。
5. "points": 核心要点数组（3 到 6 条，提炼视频中最有价值的知识点、事实或论述，每条不宜过长，基于原视频证据）。
6. "actions": 行动建议或实践指南数组（2 到 4 条，说明观众或读者可以如何应用这些知识。如果是整理者引申的建议，须注明“整理者建议：”）。
7. "synthetic": 必须为 false。

【注意事项】：
- 严格基于逐字稿事实，切勿臆测；逐字稿若有错别字或语病请结合上下文合理理解。
- 视频中未提及或未证实的内容，不要当成确凿事实。
- 仅输出纯 JSON，不添加 ```json 或 ``` 包裹，确保 json.loads 可以直接解析。"""


def clean_model_output(content: str) -> str:
    """Strip markdown code fence or wrapping if present."""
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    # If there are preamble or postamble texts outside the outer JSON {...}
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def sanitize_card_data(raw: dict[str, Any], fallback_item: dict[str, Any]) -> dict[str, Any]:
    """Ensure the parsed dictionary strictly complies with validate_card requirements."""
    title = str(raw.get("title") or fallback_item.get("title") or "未命名知识卡片").strip()[:150]
    author = str(raw.get("author") or fallback_item.get("author") or "未知作者").strip()[:150]
    source_url = str(raw.get("source_url") or fallback_item.get("source_url") or "").strip()
    if not source_url or not source_url.startswith("https://"):
        aweme_id = fallback_item.get("id", "").split("-")[-1]
        source_url = f"https://www.douyin.com/video/{aweme_id}" if aweme_id else "https://www.douyin.com"

    # Validate url host
    parsed = urlsplit(source_url)
    host = parsed.hostname or ""
    if not (host == "douyin.com" or host.endswith(".douyin.com")):
        source_url = "https://www.douyin.com"

    summary = str(raw.get("summary") or fallback_item.get("description") or "暂无摘要").strip()[:1500]
    if not summary:
        summary = "视频暂无详细摘要。"

    points = raw.get("points")
    if not isinstance(points, list) or not points:
        points = ["关注原视频获取更多细节"]
    clean_points = [str(p).strip()[:500] for p in points if str(p).strip()][:12]
    if not clean_points:
        clean_points = ["未能提炼出有效要点"]

    actions = raw.get("actions")
    if not isinstance(actions, list) or not actions:
        actions = ["结合自身实际情况理性参考"]
    clean_actions = [str(a).strip()[:500] for a in actions if str(a).strip()][:12]
    if not clean_actions:
        clean_actions = ["结合自身实际情况理性参考"]

    return {
        "title": title,
        "author": author,
        "source_url": source_url,
        "summary": summary,
        "points": clean_points,
        "actions": clean_actions,
        "synthetic": False,
    }


def call_llm(
    messages: list[dict[str, str]],
    *,
    endpoint: str = DEFAULT_ENDPOINT,
    api_key: str = "",
    model: str = DEFAULT_MODEL,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Send Chat Completion request to standard OpenAI-compatible API."""
    url = endpoint.strip() or DEFAULT_ENDPOINT
    # Auto-complete endpoint if bare base url was given
    if not url.endswith("/chat/completions"):
        url = url.rstrip("/") + ("/chat/completions" if url.endswith("/v1") else "/v1/chat/completions")

    payload = {
        "model": model.strip() or DEFAULT_MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 1500,
    }

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "YingzhiWorkbench/1.0",
    }
    if api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            result = json.loads(body)
            choices = result.get("choices") or []
            if not choices:
                raise ValueError("模型未返回有效候选结果")
            msg = choices[0].get("message") or {}
            content = msg.get("content") or ""
            return content
    except urllib.error.HTTPError as exc:
        err_msg = exc.read().decode("utf-8", errors="ignore")
        try:
            parsed_err = json.loads(err_msg)
            msg = parsed_err.get("error", {}).get("message") or err_msg
        except Exception:
            msg = err_msg or str(exc)
        raise RuntimeError(f"模型 API 请求失败 (HTTP {exc.code}): {msg[:200]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"无法连接到模型接口: {exc.reason}") from exc


def summarize_item(
    item: dict[str, Any],
    *,
    endpoint: str = DEFAULT_ENDPOINT,
    api_key: str = "",
    model: str = DEFAULT_MODEL,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Generate structured knowledge card JSON from a transcribed item."""
    title = item.get("title") or "未命名视频"
    author = item.get("author") or "未知作者"
    source_url = item.get("source_url") or ""
    transcript = item.get("transcript") or ""
    description = item.get("description") or ""

    content_to_analyze = transcript.strip()
    if not content_to_analyze:
        if description.strip():
            content_to_analyze = f"[注意：无完整逐字稿，以下为作者填写的简介文案]\n{description.strip()}"
        else:
            raise ValueError("该内容既无逐字稿也无简介，无法生成知识总结")

    user_prompt = f"""【视频基本资料】
- 视频标题：{title}
- 原作者：{author}
- 来源链接：{source_url}

【正文逐字稿/图文材料】：
{content_to_analyze[:8000]}

请基于上述材料，提取结构化知识，严格返回纯 JSON 格式。"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    raw_response = call_llm(
        messages,
        endpoint=endpoint,
        api_key=api_key,
        model=model,
        timeout=timeout,
    )

    cleaned = clean_model_output(raw_response)
    try:
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("解析结果不是有效 JSON 对象")
    except Exception as exc:
        raise ValueError(f"模型输出格式无法解析为 JSON: {exc} (原文: {cleaned[:100]}...)") from exc

    return sanitize_card_data(parsed, item)


def check_llm_connection(
    endpoint: str,
    api_key: str,
    model: str,
) -> dict[str, Any]:
    """Quick connectivity test for settings validation."""
    messages = [
        {"role": "system", "content": "You are a health checker. Respond with OK."},
        {"role": "user", "content": "ping"},
    ]
    try:
        reply = call_llm(
            messages,
            endpoint=endpoint,
            api_key=api_key,
            model=model,
            timeout=15,
        )
        return {"ok": True, "reply": reply[:100].strip()}
    except Exception as exc:
        return {"ok": False, "error": safe_error_message(exc)}
