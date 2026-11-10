"""DeepSeek chat completions. The API key is read from the environment and never logged."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class ModelError(RuntimeError):
    """The model call did not return usable text."""


def api_key() -> str:
    return os.environ.get("DEEPSEEK_API_KEY", "").strip()


def complete(messages: list[dict[str, str]], *, temperature: float = 0.2, json_mode: bool = False) -> str:
    key = api_key()
    if key == "":
        raise ModelError("还没有配置 DEEPSEEK_API_KEY。把钥匙写进 .env.local 后再分析。")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"
    payload: dict = {
        "model": model,
        "temperature": temperature,
        "messages": messages,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    request = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"content-type": "application/json", "authorization": f"Bearer {key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise ModelError(f"DeepSeek 返回 HTTP {error.code}。") from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise ModelError("没有连上 DeepSeek。请检查网络后再试。") from None
    try:
        text = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise ModelError("DeepSeek 没有返回正文。") from None
    if not isinstance(text, str) or text.strip() == "":
        raise ModelError("DeepSeek 没有返回正文。")
    return text
