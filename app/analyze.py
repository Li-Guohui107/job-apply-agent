"""Turn a resume and public search rows into the studio analysis object."""

from __future__ import annotations

import json

from app.config import TRACK_NAME, TRACKS
from app.llm import ModelError, complete
from app.search import search_public
from app.store import save_analysis

SYSTEM = """你对照简历给公开职位做匹配估计，并写一份可以粘贴的中文草稿。
只使用简历里写明的事实，以及下面给出的公开结果。不要编造公司、学历、日期、指标或链接。
分数是简历和公开描述的贴合程度，不是录取概率。
只返回一个 JSON 对象，形如：
{"headline":"","overview":"","fitScore":0,"confidence":"low","successRead":"",
 "listings":[{"url":"","fitScore":0,"fitReason":"","gaps":[]}],
 "strengths":[],"gaps":[],
 "plan":[{"when":"","title":"","actions":[]}],
 "draftSubject":"","draftBody":"","draftUrl":""}
confidence 只能是 low、medium、high。listings 里的 url 必须来自输入。草稿只写得分最高且确实存在的那一条。"""


class InputError(ValueError):
    """The desk form sent something the service will not analyze."""


def check_resume(text: str) -> str:
    resume = text.replace("\x00", "").strip()
    if len(resume) < 40:
        raise InputError("简历太短。请放上经历、项目或技能。")
    if len(resume) > 12000:
        resume = resume[:12000]
    if "示例候选人" in resume:
        raise InputError("这还是示例简历。请换成你自己的经历。")
    return resume


def check_request(payload: dict) -> tuple[list[str], list[str], int, str]:
    if not isinstance(payload, dict):
        raise InputError("请求格式不对。")
    cities = payload.get("cities")
    tracks = payload.get("tracks")
    if not isinstance(cities, list) or not cities:
        raise InputError("请至少选择一个城市。")
    if len(cities) > 8:
        raise InputError("最多选择 8 个城市。")
    clean_cities: list[str] = []
    for city in cities:
        name = str(city).strip()
        if name == "" or len(name) > 40:
            raise InputError("城市名称不正确。")
        if name not in clean_cities:
            clean_cities.append(name)
    if not isinstance(tracks, list) or not tracks:
        raise InputError("请至少选择一个方向。")
    clean_tracks = []
    for track in tracks:
        if track not in TRACKS:
            raise InputError("方向不正确。")
        if track not in clean_tracks:
            clean_tracks.append(track)
    try:
        limit = int(payload.get("limit", 8))
    except (TypeError, ValueError):
        raise InputError("条数上限不正确。") from None
    if limit < 1 or limit > 10:
        raise InputError("条数上限要在 1 到 10 之间。")
    resume = check_resume(str(payload.get("resume", "")))
    return clean_cities, clean_tracks, limit, resume


def _text(value, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:limit]


def _texts(value, limit: int, count: int) -> list[str]:
    if not isinstance(value, list):
        return []
    rows = []
    for item in value:
        text = _text(item, limit)
        if text:
            rows.append(text)
        if len(rows) >= count:
            break
    return rows


def _score(value) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, round(number)))


def _confidence(value: str) -> str:
    return value if value in ("low", "medium", "high") else "low"


def _plan(value) -> list[dict]:
    rows = []
    if isinstance(value, list):
        for item in value:
            if not isinstance(item, dict):
                continue
            title = _text(item.get("title"), 80)
            when = _text(item.get("when"), 20)
            actions = _texts(item.get("actions"), 160, 4)
            if title and when and actions:
                rows.append({"when": when, "title": title, "actions": actions})
            if len(rows) >= 4:
                break
    if len(rows) >= 2:
        return rows
    return [
        {"when": "今天", "title": "核对公开页面", "actions": ["打开检索到的链接，确认职位是否仍在招聘。"]},
        {"when": "本周", "title": "只补充简历里已有的内容", "actions": ["缺口只对照简历原文，不要编造经历。"]},
    ]


def shape_analysis(raw: dict, listings: list[dict], cities: list[str], tracks: list[str]) -> dict:
    """Keep only URLs that the search step actually returned."""
    by_url = {item["url"]: item for item in listings}
    ranked = []
    incoming = raw.get("listings") if isinstance(raw, dict) else None
    if isinstance(incoming, list):
        for item in incoming:
            if not isinstance(item, dict):
                continue
            url = item.get("url")
            source = by_url.get(url)
            if source is None:
                continue
            ranked.append(
                {
                    "title": source["title"],
                    "company": source["company"],
                    "location": source["location"],
                    "url": source["url"],
                    "track": source["track"],
                    "summary": source["summary"],
                    "fitScore": _score(item.get("fitScore")),
                    "fitReason": _text(item.get("fitReason"), 300) or "公开结果与简历的贴合需要打开页面后再核对。",
                    "gaps": _texts(item.get("gaps"), 120, 4),
                }
            )
    if not ranked:
        ranked = [
            {
                **source,
                "fitScore": 0,
                "fitReason": "模型没有给这条公开结果打分。",
                "gaps": [],
            }
            for source in listings
        ]
    ranked.sort(key=lambda item: item["fitScore"], reverse=True)
    ranked = ranked[:8]
    top = ranked[0]["fitScore"] if ranked else 0
    draft_url = raw.get("draftUrl") if isinstance(raw, dict) else ""
    if draft_url not in by_url and ranked:
        draft_url = ranked[0]["url"]
    if draft_url not in by_url:
        draft_url = ""
    return {
        "ok": True,
        "kind": "studio-analysis",
        "cities": cities,
        "tracks": tracks,
        "headline": _text(raw.get("headline") if isinstance(raw, dict) else "", 80) or "公开职位匹配估计",
        "overview": _text(raw.get("overview") if isinstance(raw, dict) else "", 700)
        or "下面只保留这次检索到的公开结果。",
        "fitScore": _score(raw.get("fitScore") if isinstance(raw, dict) else top) or top,
        "confidence": _confidence(_text(raw.get("confidence") if isinstance(raw, dict) else "", 10)),
        "successRead": _text(raw.get("successRead") if isinstance(raw, dict) else "", 500)
        or "这是简历和公开描述的贴合估计，不是录取概率。",
        "listings": ranked,
        "strengths": _texts(raw.get("strengths") if isinstance(raw, dict) else [], 160, 5),
        "gaps": _texts(raw.get("gaps") if isinstance(raw, dict) else [], 160, 6),
        "plan": _plan(raw.get("plan") if isinstance(raw, dict) else None),
        "draftSubject": _text(raw.get("draftSubject") if isinstance(raw, dict) else "", 120),
        "draftBody": (raw.get("draftBody") if isinstance(raw, dict) and isinstance(raw.get("draftBody"), str) else "")[:4000],
        "draftUrl": draft_url,
    }


def prose_for(analysis: dict) -> str:
    names = {"low": "低", "medium": "中", "high": "高"}
    cities = "、".join(analysis["cities"])
    tracks = "、".join(TRACK_NAME.get(track, track) for track in analysis["tracks"])
    confidence = names.get(analysis["confidence"], "低")
    return (
        f"本次按{cities}的{tracks}检索，保留 {len(analysis['listings'])} 条公开结果。"
        f"综合匹配估计为 {analysis['fitScore']} 分，置信度为{confidence}。"
        "投递尚未记录。"
    )


def empty_analysis(cities: list[str], tracks: list[str]) -> dict:
    return shape_analysis(
        {
            "headline": "这轮没有公开结果",
            "overview": "检索没有返回可展示的公开页面。可以换一个城市或方向再试。",
            "fitScore": 0,
            "confidence": "low",
            "successRead": "没有公开结果时不估计录取机会。",
            "listings": [],
            "strengths": [],
            "gaps": ["这次没有检索到可对照的公开职位。"],
            "plan": [
                {"when": "今天", "title": "缩小检索", "actions": ["保留一个城市和一个方向，再跑一次。"]},
                {"when": "本周", "title": "自己打开招聘页核对", "actions": ["只采用你能打开的公开职位，不要引用检索里没有的链接。"]},
            ],
            "draftSubject": "",
            "draftBody": "",
        },
        [],
        cities,
        tracks,
    )


def run_analysis(payload: dict, *, search=search_public, ask=complete, directory=None) -> dict:
    cities, tracks, limit, resume = check_request(payload)
    listings = search(cities, tracks, limit)
    if not listings:
        analysis = empty_analysis(cities, tracks)
    else:
        user = json.dumps({"resume": resume, "listings": listings}, ensure_ascii=False)
        try:
            content = ask(
                [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
                json_mode=True,
            )
            parsed = json.loads(content)
        except json.JSONDecodeError as error:
            raise ModelError("模型没有返回可解析的匹配结果。") from error
        if not isinstance(parsed, dict):
            raise ModelError("模型没有返回可解析的匹配结果。")
        analysis = shape_analysis(parsed, listings, cities, tracks)
    prose = prose_for(analysis)
    analysis_id = save_analysis(analysis, prose, directory) if directory is not None else save_analysis(analysis, prose)
    return {"id": analysis_id, "analysis": analysis, "prose": prose}
