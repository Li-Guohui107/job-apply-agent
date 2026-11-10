"""Paths and local environment loading. Secret values stay in the process environment."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_PAGE = ROOT / "web" / "studio.html"
SAMPLE_RESUME = ROOT / "data" / "resume.md"
RUNTIME = ROOT / "data" / "runtime"

TRACKS = ("computer", "agent", "algorithm")
TRACK_QUERY = {
    "computer": "计算机 软件开发 工程师 招聘",
    "agent": "Agent开发 AI Agent 工程师 招聘",
    "algorithm": "算法工程师 机器学习 招聘",
}
TRACK_NAME = {
    "computer": "计算机",
    "agent": "Agent 开发",
    "algorithm": "算法",
}


def load_env_file(path: Path) -> None:
    """Load KEY=VALUE lines that are not already set. Blank lines and comments are skipped."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line == "" or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key == "" or key in os.environ:
            continue
        os.environ[key] = value.strip().strip('"').strip("'")


def load_local_env() -> None:
    load_env_file(ROOT / ".env")
    load_env_file(ROOT / ".env.local")
