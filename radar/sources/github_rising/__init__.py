"""GitHub 별 급상승 저장소 주간 순위.

명령
  snapshot  후보 저장소들의 별 수 기록 (매일)
  report    7일 증가분으로 순위 계산 → 저장 + 페이지/RSS. summary.mode가 claude-task면 알림은 보류
  pending   최신 리포트에서 요약이 비어 있는 항목과 README 주소를 JSON으로 출력 (Claude 예약 작업용)
  enrich    --file summaries.json 의 요약을 최신 리포트에 합치고 페이지/RSS 다시 만들기
  publish   페이지/RSS 다시 만들고, 아직 안 보낸 최신 리포트를 알림으로 보내기 (한 번만)
  resend    최신 리포트 알림을 다시 보내기 (테스트용)
  site      저장된 리포트로 페이지/RSS만 다시 만들기
"""
from __future__ import annotations

import json

from . import core, render
from ...summarize import summarize

ITEM_FIELDS = ("rank", "name", "html_url", "gain", "capped", "method", "stargazers_count", "forks_count",
               "change", "prev_rank", "license", "language", "description", "topics", "created_at", "suspicious",
               "one_liner", "caveat", "install", "category")
SUMMARY_FIELDS = ("one_liner", "caveat", "install", "category")

COMMANDS = ("snapshot", "report", "pending", "enrich", "publish", "resend", "site")
site_section = render.site_section


def _mode(cfg) -> str:
    s = cfg.get("summary", {})
    if s.get("enabled") is False:
        return "off"
    return s.get("mode", "claude-task")


def _rebuild(cfg) -> None:
    for rep in core.all_reports(1000):  # oldest first, so latest.md ends up as the newest
        render.write_markdown(rep, cfg)
    render.write_feed(cfg)
    render.write_site(cfg)


def _latest() -> dict | None:
    reports = core.all_reports(1)
    return reports[-1] if reports else None


def run(command: str, cfg: dict, gh, args, log=print) -> dict | None:
    """Returns {"payloads": {...}} when there is something to notify."""
    if command == "site":
        _rebuild(cfg)
        return None
    if command == "snapshot":
        core.take_snapshot(cfg, gh, log)
        return None
    if command == "pending":
        rep = _latest()
        todo = [{"name": it["name"], "rank": it["rank"], "description": it.get("description"),
                 "topics": it.get("topics"), "license": it.get("license"), "language": it.get("language"),
                 "readme_url": f"https://raw.githubusercontent.com/{it['name']}/HEAD/README.md"}
                for it in (rep or {}).get("items", []) if not it.get("one_liner")]
        print(json.dumps({"date": rep and rep["date"], "enriched": bool(rep and rep.get("enriched")),
                          "notified": bool(rep and rep.get("notified")), "items": todo}, ensure_ascii=False, indent=1))
        return None
    if command == "enrich":
        rep = _latest()
        if not rep:
            log("no report to enrich")
            return None
        data = json.loads(open(args.file, encoding="utf-8").read())
        data = data.get("items", data) if isinstance(data, dict) else data
        if isinstance(data, list):
            data = {d["name"]: d for d in data}
        n = 0
        for it in rep["items"]:
            s = data.get(it["name"])
            if s:
                it.update({k: (s.get(k) or "").strip() for k in SUMMARY_FIELDS if k in s})
                n += 1
        rep["enriched"] = True
        core.save_report(rep)
        _rebuild(cfg)
        log(f"enriched {n}/{len(rep['items'])} items in {rep['date']}")
        return None
    if command in ("publish", "resend"):
        _rebuild(cfg)
        rep = _latest()
        if not rep or (rep.get("notified") and command == "publish"):
            log("nothing new to notify")
            return None
        rep["notified"] = True
        core.save_report(rep)
        log(f"publishing {rep['date']} (summaries: {'yes' if rep.get('enriched') else 'no'})")
        return {"payloads": render.payloads(rep, cfg)}

    # report (--as-of YYYY-MM-DD: backfill a past week from stargazer history, never notified)
    as_of = getattr(args, "as_of", None)
    if as_of:
        from datetime import datetime
        until = datetime.fromisoformat(f"{as_of}T07:00:00+09:00")
        snaps = core.list_snapshots()
        if not snaps:
            log("backfill needs at least one snapshot for the candidate list")
            return None
        cur = core.load_snapshot(snaps[-1])
        rows, meta = core.compute_gains(cfg, gh, cur, as_of, log, until=until)
        top, dropped, prev = core.rank(cfg, rows, as_of)
        report = {"date": as_of, "meta": meta,
                  "items": [{k: it.get(k) for k in ITEM_FIELDS} for it in top],
                  "dropped": dropped, "previous": prev["date"] if prev else None,
                  "enriched": False, "notified": True}
        if args.dry_run:
            log(render.markdown(report, cfg))
            return None
        if not top:
            log("backfill: nothing could be counted (token cannot read stargazers?) - not saved")
            return None
        core.save_report(report)
        _rebuild(cfg)
        log(f"saved backfill report {as_of} ({len(top)} items, API calls: {gh.calls})")
        return None
    today = core.now_local(cfg).strftime("%Y-%m-%d")
    snaps = core.list_snapshots()
    if not snaps or snaps[-1].stem != today or args.fresh:
        cur = core.take_snapshot(cfg, gh, log)
    else:
        cur = core.load_snapshot(snaps[-1])
        log(f"using today's snapshot ({len(cur['repos'])} repos)")
    rows, meta = core.compute_gains(cfg, gh, cur, today, log)
    top, dropped, prev = core.rank(cfg, rows, today)
    mode = _mode(cfg)
    if mode == "api":
        summarize(top, gh, cfg, log)
    report = {"date": today, "meta": meta,
              "items": [{k: it.get(k) for k in ITEM_FIELDS} for it in top],
              "dropped": dropped, "previous": prev["date"] if prev else None,
              "enriched": mode == "api", "notified": mode != "claude-task"}
    if args.dry_run:
        log(render.markdown(report, cfg))
        return None
    core.save_report(report)
    _rebuild(cfg)
    log(f"saved report {today} (API calls: {gh.calls})")
    if mode == "claude-task":
        log("  summary.mode=claude-task: waiting for the Claude task to enrich, then `publish` sends alerts")
        return None
    return {"payloads": render.payloads(report, cfg)}
