"""Local JSON records. Resume text is never written here."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from app.config import RUNTIME


def normalize_job_key(value: str) -> str:
    compact = re.sub(r"\s+", "-", value.strip().lower())
    return compact[:180]


def _read_json(path: Path, fallback):
    if not path.is_file():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def save_analysis(analysis: dict, prose: str, directory: Path = RUNTIME) -> str:
    from secrets import token_hex

    analysis_id = token_hex(8)
    _write_json(
        directory / "analyses" / f"{analysis_id}.json",
        {"id": analysis_id, "analysis": analysis, "prose": prose},
    )
    return analysis_id


def load_analysis(analysis_id: str, directory: Path = RUNTIME) -> dict | None:
    if not re.fullmatch(r"[a-f0-9]{16}", analysis_id):
        return None
    path = directory / "analyses" / f"{analysis_id}.json"
    if not path.is_file():
        return None
    return _read_json(path, None)


def record_submission(packet: dict, directory: Path = RUNTIME) -> dict:
    """Write one confirmed packet. The same job key is not overwritten."""
    if packet.get("confirmed") is not True:
        return {"recorded": False, "reason": "confirmed"}
    job_key = normalize_job_key(str(packet.get("jobKey", "")))
    title = str(packet.get("title", "")).strip()
    company = str(packet.get("company", "")).strip()
    location = str(packet.get("location", "")).strip()
    url = str(packet.get("url", "")).strip()
    body = str(packet.get("packet", "")).strip()
    if job_key == "" or title == "" or company == "" or url == "" or body == "":
        return {"recorded": False, "reason": "incomplete", "jobKey": job_key}
    if not url.startswith(("http://", "https://")):
        return {"recorded": False, "reason": "url", "jobKey": job_key}

    path = directory / "submissions.json"
    current = _read_json(path, {})
    if not isinstance(current, dict):
        current = {}
    if job_key in current:
        return {"recorded": False, "duplicate": True, "jobKey": job_key}

    current[job_key] = {
        "jobKey": job_key,
        "title": title[:200],
        "company": company[:200],
        "location": location[:80],
        "url": url[:500],
        "packet": body[:8000],
        "recordedAt": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(path, current)
    return {"recorded": True, "duplicate": False, "jobKey": job_key}
