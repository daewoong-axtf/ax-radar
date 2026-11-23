"""Snapshot, star-gain calculation and ranking."""
from __future__ import annotations

import json
import math
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ...github import GitHub, GitHubError

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "github_rising"
SNAP_DIR = DATA / "snapshots"
REPORT_DIR = DATA / "reports"
STATE_FILE = DATA / "state.json"

KEEP_FIELDS = ("stargazers_count", "forks_count", "created_at", "pushed_at", "description", "language",
               "html_url", "archived", "fork", "topics", "homepage")


def now_local(cfg) -> datetime:
    return datetime.now(timezone(timedelta(hours=cfg["github_rising"]["report"].get("timezone_offset_hours", 9))))


def _slim(item: dict) -> dict:
    d = {k: item.get(k) for k in KEEP_FIELDS}
    lic = item.get("license") or {}
    d["license"] = lic.get("spdx_id") if lic and lic.get("spdx_id") not in (None, "NOASSERTION") else None
    return d


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text("utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n", "utf-8")


# ---------------------------------------------------------------- snapshot

def take_snapshot(cfg, gh: GitHub, log=print) -> dict:
    today = now_local(cfg)
    fmt = lambda days: (today - timedelta(days=days)).strftime("%Y-%m-%d")
    subs = {"since_7d": fmt(7), "since_30d": fmt(30), "since_90d": fmt(90)}
    disc = cfg["github_rising"]["discovery"]
    repos: dict[str, dict] = {}
    for q in disc["queries"]:
        query = q.format(**subs)
        try:
            items = gh.search_repos(query, disc.get("pages_per_query", 1))
        except GitHubError as e:
            log(f"  search failed ({query}): {e}")
            continue
        log(f"  search {query!r}: {len(items)}")
        for it in items:
            repos[it["full_name"]] = _slim(it)

    # keep refreshing repos seen recently so next week's diff is exact
    state = _read_json(STATE_FILE, {"tracked": {}})
    cutoff = fmt(disc.get("keep_tracking_days", 35))
    tracked = {k: v for k, v in state.get("tracked", {}).items() if v >= cutoff}
    missing = [n for n in tracked if n not in repos]

    def fetch(name):
        try:
            return name, _slim(gh.repo(name))
        except GitHubError as e:
            return name, None if e.status == 404 else "keep"

    with ThreadPoolExecutor(8) as ex:
        for name, info in ex.map(fetch, missing):
            if isinstance(info, dict):
                repos[info["html_url"].split("github.com/")[-1]] = info
            elif info is None:
                tracked.pop(name, None)
    log(f"  refreshed {len(missing)} tracked repos")

    stamp = today.strftime("%Y-%m-%d")
    for name in repos:
        tracked[name] = stamp
    _write_json(STATE_FILE, {"tracked": tracked})
    snap = {"taken_at": today.isoformat(timespec="seconds"), "repos": repos}
    _write_json(SNAP_DIR / f"{stamp}.json", snap)
    log(f"snapshot {stamp}: {len(repos)} repos (API calls so far: {gh.calls})")
    return snap


def list_snapshots() -> list[Path]:
    return sorted(SNAP_DIR.glob("*.json"))


def load_snapshot(path: Path) -> dict:
    return _read_json(path, {"repos": {}})


def find_base_snapshot(today: str, window: int) -> tuple[str, dict] | None:
    """Snapshot taken `window` days ago (±1 day)."""
    target = datetime.strptime(today, "%Y-%m-%d") - timedelta(days=window)
    best = None
    for p in list_snapshots():
        d = datetime.strptime(p.stem, "%Y-%m-%d")
        diff = abs((d - target).days)
        if diff <= 1 and (best is None or diff < best[0]):
            best = (diff, p)
    if not best:
        return None
    return best[1].stem, load_snapshot(best[1])


# ---------------------------------------------------------------- filter

def _kw_regex(keywords: list[str]) -> re.Pattern:
    parts = []
    for kw in keywords:
        k = re.escape(kw.lower())
        parts.append(rf"(?<![a-z0-9]){k}(?![a-z0-9])" if len(kw) <= 3 else rf"(?<![a-z0-9]){k}")
    return re.compile("|".join(parts))


def eligible(name: str, r: dict, cfg) -> bool:
    f = cfg["github_rising"]["filter"]
    if r.get("fork") or r.get("archived"):
        return False
    if name.lower() in {x.lower() for x in f.get("exclude", [])}:
        return False
    if (r.get("stargazers_count") or 0) < f.get("min_stars", 0):
        return False
    if (r.get("forks_count") or 0) < f.get("min_forks", 0):
        return False
    if f.get("ai_only", True):
        text = " ".join([name.replace("/", " "), r.get("description") or "", " ".join(r.get("topics") or [])]).lower()
        if not _kw_regex(f["keywords"]).search(text):
            return False
    return True


# ---------------------------------------------------------------- star gains

def count_recent_stars(gh: GitHub, name: str, stars: int, since: datetime, max_pages: int):
    """Count stargazers with starred_at >= since by walking pages backwards.
    Returns (count, capped) or None when the repo is too big for the API (>40k stars)."""
    last = max(1, math.ceil(stars / 100))
    if last > 400:
        return None
    count = 0
    for i, page in enumerate(range(last, 0, -1)):
        if i >= max_pages:
            return count, True
        try:
            rows = gh.stargazer_page(name, page)
        except GitHubError:
            return None
        if not rows and page == last and last > 1:
            continue  # count was slightly stale; last page empty
        older = False
        for row in rows:
            ts = datetime.fromisoformat(row["starred_at"].replace("Z", "+00:00"))
            if ts >= since:
                count += 1
            else:
                older = True
        if older:
            return count, False
    return count, False


def compute_gains(cfg, gh: GitHub, cur: dict, today: str, log=print) -> tuple[list[dict], dict]:
    window = cfg["github_rising"]["report"]["window_days"]
    base = find_base_snapshot(today, window)
    since = datetime.fromisoformat(cur["taken_at"]) - timedelta(days=window)
    meta = {"window_days": window, "until": cur["taken_at"], "since": since.isoformat(timespec="seconds"),
            "base_snapshot": base[0] if base else None}
    base_repos = base[1]["repos"] if base else {}
    base_time = datetime.fromisoformat(base[1]["taken_at"]) if base else None
    if base:
        meta["since"] = base[1]["taken_at"]

    rows, need_boot = [], []
    for name, r in cur["repos"].items():
        if not eligible(name, r, cfg):
            continue
        row = {"name": name, **r}
        created = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
        if name in base_repos:
            row["gain"], row["method"] = r["stargazers_count"] - base_repos[name]["stargazers_count"], "snapshot"
        elif created >= (base_time or since):
            row["gain"], row["method"] = r["stargazers_count"], "new"
        else:
            need_boot.append(row)
            continue
        rows.append(row)

    bcfg = cfg["github_rising"]["bootstrap"]
    if need_boot and bcfg.get("enabled", True):
        def velocity(row):
            age = max(1.0, (datetime.now(timezone.utc) -
                            datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))).days)
            return row["stargazers_count"] / age
        need_boot.sort(key=velocity, reverse=True)
        todo = need_boot[: bcfg.get("max_repos", 250)]
        log(f"  counting recent stargazers for {len(todo)} repos (no base snapshot)")

        def work(row):
            res = count_recent_stars(gh, row["name"], row["stargazers_count"], since, bcfg.get("max_pages_per_repo", 60))
            return row, res

        with ThreadPoolExecutor(8) as ex:
            for row, res in ex.map(work, todo):
                if res is None:
                    continue
                row["gain"], row["capped"] = res
                row["method"] = "stargazers"
                rows.append(row)
    meta["candidates"] = len(rows)
    return rows, meta


# ---------------------------------------------------------------- ranking

def previous_report(today: str, min_gap_days: int = 4) -> dict | None:
    t = datetime.strptime(today, "%Y-%m-%d")
    prev = [p for p in sorted(REPORT_DIR.glob("*.json"))
            if (t - datetime.strptime(p.stem, "%Y-%m-%d")).days >= min_gap_days]
    return _read_json(prev[-1], None) if prev else None


def rank(cfg, rows: list[dict], today: str) -> tuple[list[dict], list[dict], dict | None]:
    top_n = cfg["github_rising"]["report"]["top_n"]
    ordered = sorted(rows, key=lambda r: (r["gain"], r["stargazers_count"]), reverse=True)
    top = [dict(r) for r in ordered[:top_n]]
    prev = previous_report(today)
    prev_rank = {it["name"]: it["rank"] for it in (prev or {}).get("items", [])}
    ratio = cfg["github_rising"]["filter"].get("suspicious_fork_ratio", 0.01)
    for i, r in enumerate(top, 1):
        r["rank"] = i
        p = prev_rank.get(r["name"])
        r["prev_rank"] = p
        if not prev:
            r["change"] = "-"
        elif p is None:
            r["change"] = "새로 진입"
        elif p == i:
            r["change"] = f"지난주 {p}위 ="
        elif p > i:
            r["change"] = f"지난주 {p}위 ▲{p - i}"
        else:
            r["change"] = f"지난주 {p}위 ▼{i - p}"
        stars = r["stargazers_count"] or 1
        r["suspicious"] = (r.get("forks_count") or 0) / stars < ratio and stars > 1000
    current = {r["name"] for r in top}
    gains = {r["name"]: r for r in ordered}
    dropped = []
    for it in (prev or {}).get("items", []):
        if it["name"] not in current:
            now = gains.get(it["name"])
            dropped.append({"name": it["name"], "html_url": it["html_url"], "prev_rank": it["rank"],
                            "gain": now["gain"] if now else None})
    return top, dropped, prev


def save_report(report: dict) -> Path:
    path = REPORT_DIR / f"{report['date']}.json"
    _write_json(path, report)
    return path


def all_reports(limit: int = 20) -> list[dict]:
    return [r for r in (_read_json(p, None) for p in sorted(REPORT_DIR.glob("*.json"))[-limit:]) if r]
