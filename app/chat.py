"""Answer a desk question. A job search runs only after the message names a city."""

from __future__ import annotations

import json

from app.config import TRACKS
from app.llm import complete
from app.search import search_public

CITY_WORDS = ("北京", "上海", "深圳", "杭州", "广州", "成都", "南京", "武汉", "西安", "苏州", "远程")
SYSTEM = """你是岗位系统里的中文助手。
你可以解释城市范围、方向、简历该怎么写，以及匹配分是什么。
匹配分是简历和公开描述的贴合估计，不是录取概率。
不要登录招聘网站，不要声称已经提交申请。
不要编造公司、链接、人数或经历。
用户要记录投递时，请他回到投递台的草稿页，点击「确认后记到本地」。"""


def wants_job_search(text: str) -> bool:
    return any(word in text for word in ("搜索", "招聘", "岗位", "职位"))


def cities_in(text: str) -> list[str]:
    return [city for city in CITY_WORDS if city in text]


def tracks_in(text: str) -> list[str]:
    found = []
    if any(word in text for word in ("Agent", "agent", "智能体")):
        found.append("agent")
    if any(word in text for word in ("算法", "机器学习")):
        found.append("algorithm")
    if any(word in text for word in ("计算机", "软件", "开发")) and "Agent" not in text and "agent" not in text:
        found.append("computer")
    if "软件" in text and "computer" not in found:
        found.append("computer")
    return found or list(TRACKS)


def _history(value) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    rows = []
    for item in value[-8:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            rows.append({"role": role, "content": content.strip()[:4000]})
    return rows


def reply(payload: dict, *, search=search_public, ask=complete) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("请求格式不对。")
    message = str(payload.get("message", "")).strip()
    if message == "":
        raise ValueError("请输入问题。")
    message = message[:4000]
    if wants_job_search(message) and not cities_in(message):
        return {
            "text": "请先说明城市。没有城市时不会搜索全国。",
            "searched": False,
            "listings": [],
        }
    listings = []
    searched = False
    user = message
    system = SYSTEM
    if wants_job_search(message):
        searched = True
        listings = search(cities_in(message), tracks_in(message), 5)
        system += " 用户消息里附带了这次的公开检索结果。只引用这些结果。结果为空时说明没有检索到，不要编造职位。"
        user = json.dumps({"question": message, "listings": listings}, ensure_ascii=False)
    text = ask(
        [{"role": "system", "content": system}, *_history(payload.get("history")), {"role": "user", "content": user}],
        temperature=0.3,
    )
    return {"text": text.strip()[:6000], "searched": searched, "listings": listings}
