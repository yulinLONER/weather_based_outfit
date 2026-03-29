import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from core.ai_client import AIClientError, chat_json, is_ai_enabled
from db.manager import WardrobeDatabase


@dataclass(frozen=True)
class AITagConfig:
    min_confidence: float = 0.65
    max_tags: int = 6


@dataclass(frozen=True)
class AIRecommendConfig:
    cache_ttl_seconds: int = 600
    max_candidates: int = 80


class AISettingsStore:
    def __init__(self, db: Optional[WardrobeDatabase] = None):
        self.db = db or WardrobeDatabase()

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT value FROM ai_settings WHERE key = ?", (key,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return default
        return row["value"]

    def set(self, key: str, value: str) -> None:
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO ai_settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP",
            (key, value),
        )
        conn.commit()
        conn.close()

    def as_tag_config(self) -> AITagConfig:
        min_conf = self.get("tag_min_confidence", "0.65")
        max_tags = self.get("tag_max_tags", "6")
        try:
            min_conf_f = float(min_conf)
        except Exception:
            min_conf_f = 0.65
        try:
            max_tags_i = int(max_tags)
        except Exception:
            max_tags_i = 6
        return AITagConfig(min_confidence=min_conf_f, max_tags=max_tags_i)

    def as_recommend_config(self) -> AIRecommendConfig:
        ttl = self.get("recommend_cache_ttl_seconds", "600")
        max_candidates = self.get("recommend_max_candidates", "80")
        try:
            ttl_i = int(ttl)
        except Exception:
            ttl_i = 600
        try:
            max_candidates_i = int(max_candidates)
        except Exception:
            max_candidates_i = 80
        return AIRecommendConfig(cache_ttl_seconds=ttl_i, max_candidates=max_candidates_i)


def _hash_obj(obj: Any) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _cache_get(db: WardrobeDatabase, cache_key: str) -> Optional[Dict[str, Any]]:
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT response_json, expires_at FROM api_cache WHERE cache_key = ?", (cache_key,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    try:
        expires_at = datetime.fromisoformat(row["expires_at"])
    except Exception:
        return None
    if expires_at <= datetime.utcnow():
        return None
    try:
        return json.loads(row["response_json"])
    except Exception:
        return None


def _cache_set(db: WardrobeDatabase, cache_key: str, obj: Dict[str, Any], ttl_seconds: int) -> None:
    expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO api_cache (cache_key, response_json, expires_at) VALUES (?, ?, ?)",
        (cache_key, json.dumps(obj, ensure_ascii=False), expires_at),
    )
    conn.commit()
    conn.close()


def generate_ai_tags(
    *,
    item: Dict[str, Any],
    available_tags: List[Dict[str, Any]],
    config: AITagConfig,
) -> Dict[str, Any]:
    if not is_ai_enabled():
        raise AIClientError("AI 未配置：请先在管理后台或环境变量中配置 AI_API_KEY")

    tag_names = [t["name"] for t in available_tags]

    system_prompt = "你是服装商品标签与风格分类助手。你只输出 JSON，不要输出任何其他文字。"
    user_prompt = f"""
请为下面这件衣物生成标签（支持置信度筛选与标签分类）：
衣物信息：
{json.dumps(item, ensure_ascii=False)}

约束：
1) style 只能从：休闲、商务、运动、正式 中选择一个。
2) seasons 只能从：春、夏、秋、冬 中选择 1-4 个。
3) tags 从可选标签中选择若干个，每个 tag 给出 confidence(0-1) 与 category(如 功能/面料/场景)。
4) 尽量输出不超过 {config.max_tags} 个 tag。

可选标签：
{json.dumps(tag_names, ensure_ascii=False)}
""".strip()

    schema_hint = """
{
  "style": "休闲|商务|运动|正式",
  "seasons": ["春", "夏"],
  "tags": [
    {"name": "透气", "confidence": 0.86, "category": "功能"},
    {"name": "速干", "confidence": 0.78, "category": "功能"}
  ]
}
""".strip()

    ai_obj = chat_json(system_prompt, user_prompt, schema_hint=schema_hint)
    if not isinstance(ai_obj, dict):
        raise AIClientError("AI 返回非 JSON 对象")

    tags = ai_obj.get("tags") or []
    tags = tags if isinstance(tags, list) else []
    picked: List[Dict[str, Any]] = []
    for t in tags:
        if not isinstance(t, dict):
            continue
        name = t.get("name")
        conf = t.get("confidence")
        cat = t.get("category") or "功能"
        if not isinstance(name, str) or name not in tag_names:
            continue
        try:
            conf_f = float(conf)
        except Exception:
            continue
        if conf_f < config.min_confidence:
            continue
        picked.append({"name": name, "confidence": conf_f, "category": str(cat)})
    picked.sort(key=lambda x: x["confidence"], reverse=True)
    picked = picked[: max(0, config.max_tags)]

    return {
        "style": ai_obj.get("style"),
        "seasons": ai_obj.get("seasons"),
        "tags": picked,
    }


def ai_recommend(
    *,
    weather_info: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    config: AIRecommendConfig,
    db: Optional[WardrobeDatabase] = None,
) -> Dict[str, Any]:
    db = db or WardrobeDatabase()
    cache_key = "ai_recommend:" + _hash_obj({"weather": weather_info, "candidates": candidates})
    cached = _cache_get(db, cache_key)
    if cached:
        return cached

    if not is_ai_enabled():
        raise AIClientError("AI 未配置：请先在管理后台或环境变量中配置 AI_API_KEY")

    system_prompt = "你是穿搭推荐助手。你只输出 JSON，不要输出任何其他文字。"
    user_prompt = f"""
已知天气信息：
{json.dumps(weather_info, ensure_ascii=False)}

下面是可用的衣橱候选单品（数组），请根据天气与风格生成推荐。
要求：
1) 只使用候选单品；用 title 作为展示文本。
2) 输出按“类别”分组：键是 category，值是 title 数组；每个类别最多 3 件。
3) 适当补全穿搭结构：优先给出上衣/下装/外套(需要时)/连衣裙(可替代上衣+下装)。
4) 结果放在 recommendations.推荐穿搭 下。

候选单品：
{json.dumps(candidates[: config.max_candidates], ensure_ascii=False)}
""".strip()

    schema_hint = """
{
  "recommendations": {
    "推荐穿搭": {
      "类别名": ["单品title", "单品title"]
    }
  },
  "ai_tip": "一句话建议"
}
""".strip()

    ai_obj = chat_json(system_prompt, user_prompt, schema_hint=schema_hint)
    if not isinstance(ai_obj, dict):
        raise AIClientError("AI 返回非 JSON 对象")

    _cache_set(db, cache_key, ai_obj, ttl_seconds=max(30, config.cache_ttl_seconds))
    return ai_obj

