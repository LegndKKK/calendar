"""OpenAI 兼容接口调用。"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime

_WEEKDAYS = "一二三四五六日"


class LLMError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def _base_url(config: dict) -> str:
    base = (config.get("base_url") or "").strip().rstrip("/")
    if not base:
        raise LLMError("尚未配置 Base URL")
    if not base.startswith(("http://", "https://")):
        raise LLMError("Base URL 必须以 http:// 或 https:// 开头")
    return base


def _headers(api_key: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }


def _read_error(exc: urllib.error.HTTPError) -> str:
    try:
        detail = exc.read().decode("utf-8", "replace")
    except Exception:
        detail = ""
    detail = detail.strip()
    if len(detail) > 500:
        detail = detail[:500] + "…"
    return f"HTTP {exc.code}" + (f"：{detail}" if detail else "")


def _post_json(url: str, payload: dict, api_key: str, timeout: int = 90) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=_headers(api_key),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        raise LLMError(_read_error(exc), status=exc.code) from None
    except urllib.error.URLError as exc:
        raise LLMError(f"无法连接模型服务：{exc.reason}") from None
    except TimeoutError:
        raise LLMError("模型服务响应超时") from None
    try:
        return json.loads(body)
    except ValueError:
        raise LLMError("模型返回的不是合法 JSON") from None


def _chat(config: dict, messages: list[dict], use_json_mode: bool, max_tokens: int = 1200) -> dict:
    base = _base_url(config)
    model = (config.get("model") or "").strip()
    api_key = (config.get("api_key") or "").strip()
    if not model:
        raise LLMError("尚未配置模型名")
    if not api_key:
        raise LLMError("尚未配置 API Key")

    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    if use_json_mode:
        payload["response_format"] = {"type": "json_object"}

    try:
        return _post_json(f"{base}/chat/completions", payload, api_key)
    except LLMError as exc:
        # 部分兼容服务不支持 response_format，退回普通模式再试一次。
        if use_json_mode and exc.status == 400:
            payload.pop("response_format", None)
            return _post_json(f"{base}/chat/completions", payload, api_key)
        raise


def _extract_json(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        value = json.loads(text)
    except ValueError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            raise LLMError("模型没有返回 JSON") from None
        try:
            value = json.loads(text[start : end + 1])
        except ValueError:
            raise LLMError("模型返回的 JSON 无法解析") from None
    if not isinstance(value, dict):
        raise LLMError("模型返回的 JSON 结构不正确")
    return value


def parse_text(text: str, config: dict, now: datetime) -> list[dict]:
    """调用模型解析自然语言，返回原始事件字典列表。"""
    now_text = now.strftime("%Y-%m-%d %H:%M")
    weekday = _WEEKDAYS[now.weekday()]
    system_prompt = f"""你是一个严谨的中文日历解析助手。只输出 JSON，不要输出解释、Markdown 代码块或多余文字。

输出格式：
{{"events":[{{"title":"日程标题","start":"YYYY-MM-DDTHH:MM","end":"YYYY-MM-DDTHH:MM","all_day":false,"location":"","notes":"","confidence":0.9}}]}}

规则：
1. 当前时间是 {now_text}（星期{weekday}），所有相对时间都以此为准。
2. 用户没给具体时间时：默认 09:00 开始，持续 1 小时；出现“全天/整天”时 all_day=true，start 为当天 00:00，end 为次日 00:00。
3. 用户没给日期时默认今天；如果今天的该时间已经过去，且用户没有明确说“今天”，顺延到明天。
4. 地点写入 location，其他补充信息写入 notes。
5. 一次输入可能包含多个日程，请输出多个 events。
6. 无法识别任何日程时输出 {{"events":[]}}。
7. 时间使用本地时间，不要带时区后缀。title 简洁，去掉时间和地点描述。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text},
    ]
    data = _chat(config, messages, use_json_mode=True)

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise LLMError("模型响应缺少 choices/content") from None
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    if not isinstance(content, str) or not content.strip():
        raise LLMError("模型返回了空内容")

    parsed = _extract_json(content)
    events = parsed.get("events")
    if not isinstance(events, list):
        raise LLMError("模型返回的 JSON 缺少 events 数组")
    return [event for event in events if isinstance(event, dict)]


def test_connection(config: dict) -> list[str]:
    """测试连通性，返回可用模型 id 列表（可能为空）。"""
    base = _base_url(config)
    api_key = (config.get("api_key") or "").strip()
    if not api_key:
        raise LLMError("请先填写 API Key")

    request = urllib.request.Request(f"{base}/models", headers=_headers(api_key), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8", "replace"))
        models = data.get("data") if isinstance(data, dict) else None
        if isinstance(models, list):
            return [m.get("id", "") for m in models if isinstance(m, dict) and m.get("id")]
        return []
    except urllib.error.HTTPError as exc:
        if exc.code in (404, 405):
            # 有些兼容服务没有 /models，用一次最小对话验证。
            _chat(
                config,
                [{"role": "user", "content": "ping"}],
                use_json_mode=False,
                max_tokens=5,
            )
            return []
        raise LLMError(_read_error(exc)) from None
    except urllib.error.URLError as exc:
        raise LLMError(f"无法连接模型服务：{exc.reason}") from None
    except ValueError:
        raise LLMError("模型服务返回的不是合法 JSON") from None
