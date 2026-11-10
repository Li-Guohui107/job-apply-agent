"""Checks that do not call DeepSeek or the public web."""

from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory

from app.analyze import InputError, check_resume, run_analysis, shape_analysis
from app.chat import reply
from app.search import build_queries, parse_results, search_public, unwrap_url
from app.server import StudioHandler
from app.store import normalize_job_key, record_submission
from http.server import ThreadingHTTPServer


FIXTURE = """
<a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fjobs.example.com%2Fagent">
  Agent 开发工程师
</a>
<a class="result__snippet" href="https://jobs.example.com/agent">上海公开职位，负责工具调用。</a>
<a class="result__a" href="https://jobs.example.com/direct">算法工程师</a>
"""


class SearchTests(unittest.TestCase):
    def test_queries_keep_city_and_track(self) -> None:
        queries = build_queries(["上海"], ["agent"])
        self.assertEqual(len(queries), 1)
        self.assertIn("上海", queries[0]["query"])
        self.assertIn("Agent开发", queries[0]["query"])
        self.assertEqual(queries[0]["track"], "agent")

    def test_unwraps_redirect_and_parses_rows(self) -> None:
        self.assertEqual(unwrap_url("https://duckduckgo.com/l/?uddg=https%3A%2F%2Fjobs.example.com%2Fagent"), "https://jobs.example.com/agent")
        rows = parse_results(FIXTURE)
        self.assertEqual(rows[0]["url"], "https://jobs.example.com/agent")
        self.assertIn("工具调用", rows[0]["summary"])
        self.assertEqual(rows[1]["url"], "https://jobs.example.com/direct")

    def test_search_dedupes_and_caps(self) -> None:
        def fetch(_query: str) -> str:
            return FIXTURE

        rows = search_public(["上海", "北京"], ["agent"], 1, fetch=fetch)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["location"], "上海")
        self.assertEqual(rows[0]["company"], "jobs.example.com")


class AnalysisTests(unittest.TestCase):
    def test_sample_resume_is_rejected(self) -> None:
        with self.assertRaises(InputError):
            check_resume("示例候选人，做过很多年的软件开发，项目和技能都写在这里。")

    def test_unknown_urls_are_dropped(self) -> None:
        listings = [
            {
                "title": "Agent 开发",
                "company": "jobs.example.com",
                "location": "上海",
                "url": "https://jobs.example.com/agent",
                "track": "agent",
                "summary": "公开摘要",
            }
        ]
        shaped = shape_analysis(
            {
                "headline": "上海 Agent",
                "fitScore": 140,
                "confidence": "medium",
                "listings": [
                    {"url": "https://jobs.example.com/agent", "fitScore": 61, "fitReason": "简历写了工具调用。", "gaps": []},
                    {"url": "https://invented.example/job", "fitScore": 99, "fitReason": "不该留下。", "gaps": []},
                ],
                "draftUrl": "https://invented.example/job",
            },
            listings,
            ["上海"],
            ["agent"],
        )
        self.assertEqual(len(shaped["listings"]), 1)
        self.assertEqual(shaped["listings"][0]["url"], "https://jobs.example.com/agent")
        self.assertEqual(shaped["fitScore"], 100)
        self.assertEqual(shaped["draftUrl"], "https://jobs.example.com/agent")

    def test_analysis_saves_without_resume(self) -> None:
        def search(_cities, _tracks, _limit):
            return [
                {
                    "title": "Agent 开发",
                    "company": "jobs.example.com",
                    "location": "上海",
                    "url": "https://jobs.example.com/agent",
                    "track": "agent",
                    "summary": "公开摘要",
                }
            ]

        def ask(_messages, temperature=0.2, json_mode=False):
            return json.dumps(
                {
                    "headline": "上海 Agent 匹配估计",
                    "overview": "只对照这一条公开结果。",
                    "fitScore": 60,
                    "confidence": "low",
                    "successRead": "这不是录取概率。",
                    "listings": [{"url": "https://jobs.example.com/agent", "fitScore": 60, "fitReason": "摘要提到工具调用。", "gaps": ["缺项目时间"]}],
                    "strengths": ["简历写了 Python"],
                    "gaps": ["缺项目时间"],
                    "plan": [
                        {"when": "今天", "title": "打开链接", "actions": ["核对是否仍在招聘。"]},
                        {"when": "本周", "title": "补时间", "actions": ["只写简历里已有的项目时间。"]},
                    ],
                    "draftSubject": "应聘",
                    "draftBody": "您好。",
                    "draftUrl": "https://jobs.example.com/agent",
                }
            )

        with TemporaryDirectory() as tmp:
            result = run_analysis(
                {
                    "cities": ["上海"],
                    "tracks": ["agent"],
                    "limit": 5,
                    "resume": "林舟，2022 年入职。经历：后端开发。项目：检索工具。技能：Python。学历：本科。",
                },
                search=search,
                ask=ask,
                directory=Path(tmp),
            )
            saved = json.loads((Path(tmp) / "analyses" / f"{result['id']}.json").read_text(encoding="utf-8"))
        self.assertNotIn("resume", json.dumps(saved, ensure_ascii=False))
        self.assertEqual(saved["analysis"]["fitScore"], 60)
        self.assertIn("尚未记录", saved["prose"])


class RecordTests(unittest.TestCase):
    def test_duplicate_key_is_not_overwritten(self) -> None:
        self.assertEqual(normalize_job_key(" Example Job "), "example-job")
        packet = {
            "confirmed": True,
            "jobKey": "Example Job",
            "title": "Agent 开发",
            "company": "示例公司",
            "location": "上海",
            "url": "https://jobs.example.com/agent",
            "packet": "您好。",
        }
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = record_submission(packet, root)
            second = record_submission(packet, root)
            refused = record_submission({**packet, "confirmed": False}, root)
        self.assertTrue(first["recorded"])
        self.assertTrue(second["duplicate"])
        self.assertFalse(refused["recorded"])


class ChatTests(unittest.TestCase):
    def test_search_without_a_city_does_not_call_the_model(self) -> None:
        def explode(*_args, **_kwargs):
            raise AssertionError("should not search or call the model")

        result = reply({"message": "搜索 Agent 岗位"}, search=explode, ask=explode)
        self.assertIn("城市", result["text"])
        self.assertFalse(result["searched"])


class HttpTests(unittest.TestCase):
    def test_health_and_sample_resume(self) -> None:
        with TemporaryDirectory() as tmp:
            StudioHandler.runtime = Path(tmp)

            def search(*_args, **_kwargs):
                raise AssertionError("sample resume must stop first")

            StudioHandler.search = staticmethod(search)
            server = ThreadingHTTPServer(("127.0.0.1", 0), StudioHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_address[1]
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=5) as response:
                    health = json.loads(response.read().decode("utf-8"))
                self.assertTrue(health["ok"])
                body = json.dumps(
                    {
                        "cities": ["上海"],
                        "tracks": ["agent"],
                        "limit": 5,
                        "resume": "示例候选人，做过很多年的软件开发，项目和技能都写在这里。",
                    }
                ).encode("utf-8")
                request = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/analyze",
                    data=body,
                    headers={"content-type": "application/json"},
                )
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(request, timeout=5)
                self.assertEqual(caught.exception.code, 400)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
