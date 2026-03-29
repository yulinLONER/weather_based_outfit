import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from db.manager import WardrobeDatabase


@dataclass(frozen=True)
class AIConfig:
    api_base_url: str
    api_key: str
    model: str
    timeout_seconds: int = 30


class AIClientError(RuntimeError):
    pass


def _load_ai_config() -> Optional[AIConfig]:
    """从环境变量和数据库加载 AI 配置。优先级：环境变量 > 数据库设置"""
    # 首先从环境变量获取
    api_key = os.environ.get("AI_API_KEY")
    api_base_url = os.environ.get("AI_API_BASE_URL", "https://api.openai.com").rstrip("/")
    model = os.environ.get("AI_MODEL", "gpt-4o-mini")
    timeout_raw = os.environ.get("AI_TIMEOUT_SECONDS", "30")
    
    # 如果环境变量中没有，再尝试从数据库读取
    if not api_key:
        try:
            db = WardrobeDatabase()
            conn = db.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT key, value FROM ai_settings")
            settings = {row["key"]: row["value"] for row in cur.fetchall()}
            conn.close()
            
            api_key = settings.get("api_key")
            api_base_url = settings.get("api_base_url") or api_base_url
            model = settings.get("model") or model
            timeout_raw = settings.get("timeout_seconds") or timeout_raw
        except Exception:
            pass  # 数据库配置可选，使用默认值
    
    if not api_key:
        return None
    
    try:
        timeout_seconds = int(timeout_raw)
    except (ValueError, TypeError):
        timeout_seconds = 30
    
    return AIConfig(api_base_url=api_base_url, api_key=api_key, model=model, timeout_seconds=timeout_seconds)


def is_ai_enabled() -> bool:
    return _load_ai_config() is not None


def _extract_json_object(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)

    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.IGNORECASE)
    if fenced:
        return json.loads(fenced.group(1))

    brace = re.search(r"(\{[\s\S]*\})", text)
    if brace:
        return json.loads(brace.group(1))

    raise AIClientError("模型未返回可解析的 JSON 对象")


def chat_json(system_prompt: str, user_prompt: str, *, schema_hint: str) -> Dict[str, Any]:
    cfg = _load_ai_config()
    if not cfg:
        raise AIClientError("AI 未配置：请设置环境变量 AI_API_KEY（以及可选 AI_API_BASE_URL、AI_MODEL）")

    url = f"{cfg.api_base_url}/v1/chat/completions"
    headers = {"Authorization": f"Bearer {cfg.api_key}", "Content-Type": "application/json"}
    payload = {
        "model": cfg.model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt.strip()},
            {
                "role": "user",
                "content": (user_prompt.strip() + "\n\n" + "输出要求(JSON):\n" + schema_hint.strip()).strip(),
            },
        ],
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=cfg.timeout_seconds)
    except Exception as e:
        raise AIClientError(f"AI 请求失败：{e}") from e

    if resp.status_code >= 400:
        raise AIClientError(f"AI 请求返回错误：HTTP {resp.status_code} {resp.text[:500]}")

    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except Exception as e:
        raise AIClientError("AI 返回结构异常，未找到 choices[0].message.content") from e

    return _extract_json_object(content)
