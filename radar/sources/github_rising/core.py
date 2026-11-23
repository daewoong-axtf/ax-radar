"""Snapshot, star-gain calculation and ranking."""
from __future__ import annotations

import json
import math
import re
import time
import urllib.parse
import urllib.request
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

TRENDING_URL = "https://github.com/trending/{lang}?since={period}"
_ARTICLE = re.compile(r'<article[^>]*class="[^"]*Box-row[^"]*"[^>]*>(.*?)</article>', re.S)
_H2_LINK = re.compile(r'<h2[^>]*>.*?href="/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"', re.S)


def parse_trending(page: str) -> list[str]:
    """owner/name list from a github.com/trending HTML page, in page order."""
    names = []
    for block in _ARTICLE.findall(page):
        m = _H2_LINK.search(block)
        if m and m.group(1) not in names:
            names.append(m.group(1))
    return names


def fetch_trending(cfg, log=print) -> list[str]:
    """Repos on GitHub Trending (no official API, so we read the HTML page).
    Only used to find candidates; star gains are still counted by us."""
    tcfg = cfg["github_rising"]["discovery"].get("trending", {})
    if tcfg.get("enabled", True) is False:
        return []
    names: list[str] = []
    for lang in tcfg.get("languages", [""]):
        for period in tcfg.get("periods", ["daily", "weekly"]):
            url = TRENDING_URL.format(lang=urllib.parse.quote(lang), period=period).replace("trending/?", "trending?")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (ax-radar)", "Accept": "text/html"})
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    found = parse_trending(resp.read().decode("utf-8", "replace"))
            except Exception as e:  # trending is a bonus source; never fail the snapshot over it
                log(f"  trending {lang or 'all'}/{period} failed: {e}")
                continue
            log(f"  trending {lang or 'all'}/{period}: {len(found)}")
            names += [n for n in found if n not in names]
            time.sleep(1)
    return names


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
    trending = fetch_trending(cfg, log)
    missing = [n for n in dict.fromkeys(list(tracked) + trending) if n not in repos]
    log(f"  trending: {len(trending)} repos ({sum(1 for n in trending if n not in repos)} not found by search)")

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
            elif name in trending and name not in tracked:
                log(f"  could not fetch trending repo {name}")
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

STARS_QUERY = """query($owner:String!,$name:String!,$before:String){
  repository(owner:$owner,name:$name){
    stargazerCount
    stargazers(last:100,before:$before,orderBy:{field:STARRED_AT,direction:ASC}){
      totalCount edges{starredAt} pageInfo{startCursor hasPreviousPage}}}}"""


def _count_graphql(gh: GitHub, name: str, since: datetime, max_pages: int, until: datetime | None = None):
    """Walk backwards from the newest star (no 40k limit) and stop at the first star older than `since`."""
    owner, repo = name.split("/", 1)
    count, before, prev_ts = 0, None, None
    for _ in range(max_pages):
        data = gh.graphql(STARS_QUERY, {"owner": owner, "name": repo, "before": before})
        repo_data = (data or {}).get("repository") or {}
        conn = repo_data.get("stargazers")
        if conn is None:
            return None
        if before is None and not conn["edges"] and repo_data.get("stargazerCount"):
            raise GitHubError(0, f"graphql returned no stargazers for {name} "
                                 f"(stargazerCount={repo_data.get('stargazerCount')}, totalCount={conn.get('totalCount')})")
        if before is None and conn["edges"]:
            first = conn["edges"][-1]["starredAt"]
            if not getattr(gh, "_logged_sample", False):
                gh._logged_sample = True
                print(f"    sample {name}: newest starredAt={first}, page={len(conn['edges'])}, total={conn.get('totalCount')}")
        for edge in reversed(conn["edges"]):  # page is oldest->newest; walk newest first
            ts = datetime.fromisoformat(edge["starredAt"].replace("Z", "+00:00"))
            if prev_ts is not None and ts > prev_ts + timedelta(seconds=1):
                raise GitHubError(0, f"stargazers not in time order for {name}")
            prev_ts = ts
            if ts < since:
                return count, False
            if until is None or ts < until:
                count += 1
        if not conn["pageInfo"]["hasPreviousPage"]:
            return count, False
        before = conn["pageInfo"]["startCursor"]
    return count, True


def _count_rest(gh: GitHub, name: str, stars: int, since: datetime, max_pages: int, until: datetime | None = None):
    """Oldest-first REST list walked backwards from the last page (only up to 40k stars)."""
    last = max(1, math.ceil(stars / 100))
    if last > 400:
        return None
    count = 0
    for i, page in enumerate(range(last, 0, -1)):
        if i >= max_pages:
            return count, True
        rows = gh.stargazer_page(name, page)
        if not rows and page == last and last > 1:
            continue  # count was slightly stale; last page empty
        older = False
        for row in rows:
            ts = datetime.fromisoformat(row["starred_at"].replace("Z", "+00:00"))
            if ts < since:
                older = True
            elif until is None or ts < until:
                count += 1
        if older:
            return count, False
    return count, False


def count_recent_stars(gh: GitHub, name: str, stars: int, since: datetime, max_pages: int, errors: list | None = None,
                       until: datetime | None = None):
    """Count stars given since `since`. Returns (count, capped) or None if it could not be counted."""
    for method in ("graphql", "rest"):
        if method == "graphql" and not getattr(gh, "token", None):
            continue
        try:
            if method == "graphql":
                res = _count_graphql(gh, name, since, max_pages, until)
            else:
                res = _count_rest(gh, name, stars, since, max_pages, until)
            if res is not None:
                return res
        except GitHubError as e:
            if errors is not None:
                errors.append(f"{method} {name}: {e}")
    return None


def compute_gains(cfg, gh: GitHub, cur: dict, today: str, log=print,
                  until: datetime | None = None) -> tuple[list[dict], dict]:
    """`until` set = backfill: count stars given in [until - window, until) from stargazer history."""
    window = cfg["github_rising"]["report"]["window_days"]
    base = None if until else find_base_snapshot(today, window)
    end = until or datetime.fromisoformat(cur["taken_at"])
    since = end - timedelta(days=window)
    meta = {"window_days": window, "until": end.isoformat(timespec="seconds"),
            "since": since.isoformat(timespec="seconds"), "base_snapshot": base[0] if base else None}
    if until:
        meta["backfill"] = True
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
        if until and created >= until:
            continue
        if until:
            need_boot.append(row)
            continue
        if name in base_repos:
            row["gain"], row["method"] = r["stargazers_count"] - base_repos[name]["stargazers_count"], "snapshot"
        elif created >= (base_time or since):
            row["gain"], row["method"] = r["stargazers_count"], "new"
        else:
            need_boot.append(row)
            continue
        rows.append(row)

    bcfg = cfg["github_rising"]["bootstrap"]
    if need_boot and bcfg.get("enabled", True) and bcfg.get("gharchive", True):
        new_rows = [r for r in rows if r.get("method") == "new"]
        counts = gharchive_star_counts([r["name"] for r in need_boot + new_rows], since, end, log)
        if counts is not None:
            # calibration: repos created inside the window have exact gains (= total stars)
            cal = sorted(new_rows, key=lambda r: r["gain"], reverse=True)[:5]
            for r in cal:
                log(f"    calibration {r['name']}: total {r['gain']} vs gharchive {counts.get(r['name'])}")
            ratios = [counts.get(r["name"], 0) / r["gain"] for r in cal if r["gain"] >= 200 and counts.get(r["name"])]
            if ratios:
                meta["gharchive_coverage"] = round(sorted(ratios)[len(ratios) // 2], 3)
                log(f"    gharchive coverage (median) {meta['gharchive_coverage']}")
            coverage = meta.get("gharchive_coverage")
            if coverage is None or len(ratios) < 3:
                coverage = _last_coverage() or coverage
            for row in need_boot:
                raw = counts.get(row["name"], 0)
                row["method"], row["gharchive_raw"] = "gharchive", raw
                if coverage:
                    # GH Archive here is a small sample of all events: scale back up to an estimate
                    est = raw / coverage
                    row["gain"] = min(int(round(est, -2 if est >= 1000 else -1)), row["stargazers_count"])
                    row["estimated"] = True
                else:
                    row["gain"] = raw
                rows.append(row)
            meta["gharchive_coverage_used"] = coverage
            need_boot = []
            meta["source"] = "gharchive"
    if need_boot and bcfg.get("enabled", True):
        def velocity(row):
            age = max(1.0, (datetime.now(timezone.utc) -
                            datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))).days)
            return row["stargazers_count"] / age
        need_boot.sort(key=velocity, reverse=True)
        todo = need_boot[: bcfg.get("max_repos", 250)]
        log(f"  counting recent stargazers for {len(todo)} repos (no base snapshot)")

        errors: list[str] = []
        ok = [0]

        def work(row):
            if not ok[0] and len(errors) >= 20:  # token can't read stargazers at all: stop wasting calls
                return row, None
            pages = bcfg.get("max_pages_per_repo", 60) * (2 if until else 1)
            res = count_recent_stars(gh, row["name"], row["stargazers_count"], since, pages, errors, until)
            return row, res

        with ThreadPoolExecutor(8) as ex:
            for row, res in ex.map(work, todo):
                if res is None:
                    continue
                ok[0] += 1
                row["gain"], row["capped"] = res
                row["method"] = "stargazers"
                rows.append(row)
        counted = sum(1 for r in rows if r.get("method") == "stargazers")
        log(f"  counted {counted}/{len(todo)} repos; {len(errors)} errors")
        for err in errors[:3]:
            log(f"    {err}")
        if errors and not counted:
            log("  hint: this token cannot read stargazers. GH_PAT must be a classic personal access token "
                "with no scopes (fine-grained tokens are refused) for exact first-week counts; "
                "from the second week daily snapshots make this unnecessary.")
            meta["bootstrap_failed"] = True
    meta["candidates"] = len(rows)
    return rows, meta


# ---------------------------------------------------------------- GH Archive (public ClickHouse)

def _last_coverage() -> float | None:
    for rep in reversed(all_reports(1000)):
        c = rep.get("meta", {}).get("gharchive_coverage")
        if c:
            return c
    return None


CLICKHOUSE_URL = "https://play.clickhouse.com/?user=play"


def gharchive_star_counts(names: list[str], since: datetime, until: datetime, log=print) -> dict[str, int] | None:
    """Stars (WatchEvent) per repo in [since, until) from the public GH Archive dataset.
    One query for every repo, no GitHub token needed. Returns None if the service is unreachable."""
    import urllib.request

    def lit(x: str) -> str:
        return "'" + x.replace("\\", "\\\\").replace("'", "\\'") + "'"

    fmt = lambda d: d.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    sql = ("SELECT repo_name, count() AS n FROM github_events WHERE event_type = 'WatchEvent' "
           f"AND created_at >= '{fmt(since)}' AND created_at < '{fmt(until)}' "
           f"AND repo_name IN ({', '.join(lit(n) for n in names)}) GROUP BY repo_name FORMAT JSON")
    fresh_sql = "SELECT max(created_at) AS t FROM github_events WHERE event_type = 'WatchEvent' FORMAT JSON"
    try:
        def q(text):
            req = urllib.request.Request(CLICKHOUSE_URL, data=text.encode(), method="POST",
                                         headers={"User-Agent": "ai-dev-radar"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read())["data"]
        latest = q(fresh_sql)[0]["t"]
        latest_dt = datetime.fromisoformat(latest.replace(" ", "T")).replace(tzinfo=timezone.utc)
        if latest_dt < until - timedelta(hours=12):
            log(f"  gharchive: data only up to {latest} UTC, too old for this window")
            return None
        rows = q(sql)
    except Exception as e:  # noqa: BLE001 - optional source
        log(f"  gharchive: unavailable ({e})")
        return None
    counts = {n: 0 for n in names}
    lower = {n.lower(): n for n in names}
    for r in rows:
        name = lower.get(r["repo_name"].lower())
        if name:
            counts[name] = int(r["n"])
    log(f"  gharchive: counted stars for {len(names)} repos (data up to {latest} UTC)")
    return counts


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
