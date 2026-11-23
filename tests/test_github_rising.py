"""Offline tests: python -m unittest discover tests"""
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from radar.__main__ import ROOT, load_cfg
from radar.sources.github_rising import core, render

CFG = load_cfg(str(ROOT / "config.toml"))
UTC = timezone.utc


class FakeGH:
    """Stargazers: `n` stars, one every `step` hours ending now."""
    calls = 0

    def __init__(self, n, step_hours):
        now = datetime.now(UTC)
        self.times = [now - timedelta(hours=step_hours * (n - 1 - i)) for i in range(n)]

    def stargazer_page(self, name, page):
        rows = self.times[(page - 1) * 100: page * 100]
        return [{"starred_at": t.strftime("%Y-%m-%dT%H:%M:%SZ")} for t in rows]


def repo(stars, forks=50, created="2024-01-01T00:00:00Z", desc="LLM agent framework"):
    return {"stargazers_count": stars, "forks_count": forks, "created_at": created, "description": desc,
            "html_url": "https://github.com/x/y", "archived": False, "fork": False, "topics": [], "license": "MIT"}


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for attr, sub in [("SNAP_DIR", "snapshots"), ("REPORT_DIR", "reports")]:
            p = mock.patch.object(core, attr, self.tmp / sub)
            p.start()
            self.addCleanup(p.stop)
        (self.tmp / "snapshots").mkdir()
        (self.tmp / "reports").mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_count_recent_stars(self):
        gh = FakeGH(1000, 1)  # 1 star/hour -> 168 in 7 days
        since = datetime.now(UTC) - timedelta(days=7)
        self.assertEqual(core.count_recent_stars(gh, "x/y", 1000, since, 60), (168, False))
        self.assertEqual(core.count_recent_stars(gh, "x/y", 1000, since, 1), (100, True))
        self.assertIsNone(core.count_recent_stars(gh, "x/y", 50000, since, 60))

    def test_count_recent_stars_graphql(self):
        rest = FakeGH(1000, 1)
        oldest_first = rest.times

        class GQL:
            token = "x"

            def graphql(self, q, v):
                end = int(v["before"]) if v["before"] else len(oldest_first)
                start = max(0, end - 100)
                edges = [{"starredAt": t.strftime("%Y-%m-%dT%H:%M:%SZ")} for t in oldest_first[start:end]]
                return {"repository": {"stargazers": {"edges": edges, "pageInfo": {
                    "startCursor": str(start), "hasPreviousPage": start > 0}}}}

        since = datetime.now(UTC) - timedelta(days=7)
        self.assertEqual(core.count_recent_stars(GQL(), "x/y", 50000, since, 60), (168, False))
        self.assertEqual(core.count_recent_stars(GQL(), "x/y", 50000, since, 1), (100, True))
        until, since2 = since, since - timedelta(days=7)
        self.assertEqual(core.count_recent_stars(GQL(), "x/y", 50000, since2, 60, None, until), (168, False))

    def test_keyword_filter(self):
        self.assertTrue(core.eligible("a/agentkit", repo(500), CFG))
        self.assertFalse(core.eligible("a/fonts", repo(500, desc="a nice font"), CFG))
        self.assertFalse(core.eligible("a/maize", repo(500, desc="said rain"), CFG))  # no 'ai' substring hits
        self.assertFalse(core.eligible("a/agentkit", repo(500, forks=1), CFG))

    def test_snapshot_diff_and_rank_change(self):
        now = datetime.now(timezone(timedelta(hours=9)))
        week_ago = now - timedelta(days=7)
        base = {"taken_at": week_ago.isoformat(), "repos": {"a/agent-one": repo(1000), "a/agent-two": repo(500)}}
        (self.tmp / "snapshots" / f"{week_ago:%Y-%m-%d}.json").write_text(json.dumps(base))
        prev = {"date": f"{week_ago:%Y-%m-%d}", "items": [
            {"name": "a/agent-two", "rank": 1, "html_url": "u"}, {"name": "a/gone-llm", "rank": 2, "html_url": "u"}]}
        (self.tmp / "reports" / f"{week_ago:%Y-%m-%d}.json").write_text(json.dumps(prev))
        cur = {"taken_at": now.isoformat(), "repos": {
            "a/agent-one": repo(1900), "a/agent-two": repo(800),
            "a/new-llm": repo(5000, created=(now - timedelta(days=2)).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))}}
        today = f"{now:%Y-%m-%d}"
        rows, meta = core.compute_gains(CFG, None, cur, today, log=lambda *a: None)
        self.assertEqual(meta["base_snapshot"], f"{week_ago:%Y-%m-%d}")
        gains = {r["name"]: (r["gain"], r["method"]) for r in rows}
        self.assertEqual(gains, {"a/agent-one": (900, "snapshot"), "a/agent-two": (300, "snapshot"),
                                 "a/new-llm": (5000, "new")})
        top, dropped, _ = core.rank(CFG, rows, today)
        self.assertEqual([(t["name"], t["change"]) for t in top],
                         [("a/new-llm", "새로 진입"), ("a/agent-one", "새로 진입"), ("a/agent-two", "지난주 1위 ▼2")])
        self.assertEqual([d["name"] for d in dropped], ["a/gone-llm"])
        report = {"date": today, "meta": meta, "items": top, "dropped": dropped}
        self.assertIn("BEST 3", render.markdown(report, CFG))
        self.assertEqual(len(render.slack_payload(report, CFG)["blocks"]), 3 + 3 + 2 + 1)  # header,context,divider + items + dropped(divider,section) + link



class TrendingParseTest(unittest.TestCase):
    def test_parse_trending(self):
        from radar.sources.github_rising.core import parse_trending
        page = """
<article class="Box-row">
  <div class="float-right"><a href="/login?return_to=%2Fmeta%2Fastryx">Star</a></div>
  <h2 class="h3 lh-condensed">
    <a data-hydro-click="{}" href="/meta/astryx" class="Link">
      <svg></svg><span class="text-normal">meta /</span> astryx</a>
  </h2>
  <a href="/meta/astryx/stargazers">32,313</a>
</article>
<article class="Box-row"><h2 class="h3 lh-condensed"><a href="/GoogleChrome/modern-web-guidance">x</a></h2></article>
<article class="Box-row"><h2 class="h3"><a href="/meta/astryx">dup</a></h2></article>
"""
        self.assertEqual(parse_trending(page), ["meta/astryx", "GoogleChrome/modern-web-guidance"])

if __name__ == "__main__":
    unittest.main()
