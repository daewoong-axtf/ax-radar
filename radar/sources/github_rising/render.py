"""Markdown report, Atom feed, Slack / Discord / webhook payloads."""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from .core import ROOT, all_reports

REPORTS = ROOT / "reports" / "github-rising"
PUBLIC = ROOT / "public" / "github-rising"

def base_url(cfg) -> str:
    return (cfg.get("site", {}).get("base_url") or "").rstrip("/")


ORD = ["첫째", "둘째", "셋째", "넷째", "다섯째"]


def title_for(report: dict, cfg) -> str:
    end = datetime.fromisoformat(report["meta"]["until"])
    week = ORD[min((end.day - 1) // 7, 4)]
    return f"{end.month}월 {week} 주 {cfg['github_rising']['report']['title_prefix']} BEST {len(report['items'])}"


def fmt_gain(it: dict) -> str:
    g = it.get("gain")
    if g is None:
        return "?"
    return f"+{g:,}" + ("+" if it.get("capped") else "")


def _period(report: dict) -> str:
    s = datetime.fromisoformat(report["meta"]["since"])
    u = datetime.fromisoformat(report["meta"]["until"])
    return f"{s:%Y-%m-%d %H:%M} ~ {u:%Y-%m-%d %H:%M} (KST)"


def one_liner(it: dict) -> str:
    return it.get("one_liner") or (it.get("description") or "").strip() or "-"


def caveat(it: dict) -> str:
    parts = [it["caveat"]] if it.get("caveat") else []
    if it.get("suspicious"):
        parts.append("⚠ 별 대비 포크가 아주 적어요 (가짜 스타 의심)")
    if not it.get("license"):
        parts.append("라이선스 표기 없음")
    return " · ".join(parts) or "-"


# ---------------------------------------------------------------- markdown

def markdown(report: dict, cfg) -> str:
    items, dropped = report["items"], report["dropped"]
    methods = {it.get("method") for it in items}
    lines = [f"# {title_for(report, cfg)}", "",
             f"TOP 시리즈 · {report['date']}", "",
             f"> 집계 기간: {_period(report)}. GitHub API로 별 수를 직접 세서 만든 순위예요. "
             "GitHub 공식 트렌딩 순위가 아니에요."]
    if report["meta"].get("bootstrap_failed"):
        lines.append("> 첫 주라 7일 전 기록이 없고 별 기록도 읽지 못해서, 이번 주에 새로 생긴 저장소만 집계했어요. "
                     "다음 주부터는 매일 기록과 비교해서 전체 후보를 집계해요.")
    if "stargazers" in methods:
        lines.append("> 7일 전 기록이 없는 저장소는 stargazers API의 별 누른 시각으로 셌어요. "
                     "`+N+`는 상한까지만 센 값이에요.")
    lines += ["", "| 순위 | 저장소 | 별 증가 | 지난주 대비 | 라이선스 | 한 줄 | 단, 확인할 것 |",
              "|---|---|---|---|---|---|---|"]
    for it in items:
        cell = lambda s: (s or "-").replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {it['rank']} | [{it['name']}]({it['html_url']}) | {fmt_gain(it)} | {it['change']} | "
                     f"{it.get('license') or '-'} | {cell(one_liner(it))} | {cell(caveat(it))} |")
    installs = [it for it in items if it.get("install")]
    if installs:
        lines += ["", "## 바로 써 보기 (설치 한 줄)", ""]
        for it in installs[:5]:
            lines += [f"**{it['rank']}위 {it['name']}**", "", "```bash", it["install"], "```", ""]
    if dropped:
        lines += ["", "## 빠진 곳", ""]
        for d in dropped:
            g = f" (이번 주 +{d['gain']:,})" if d.get("gain") is not None else ""
            lines.append(f"- [{d['name']}]({d['html_url']}) · 지난주 {d['prev_rank']}위{g}")
    lines += ["", "## 출처", "",
              "- GitHub REST API: 검색(`/search/repositories`), 저장소 정보(`/repos`), "
              "별 기록(`/repos/{owner}/{repo}/stargazers`)",
              f"- 후보 {report['meta']['candidates']}개 중 별 증가 순. 필터: 포크 {cfg['github_rising']['filter']['min_forks']}개 이상"
              + (", AI 관련 키워드" if cfg['github_rising']['filter'].get('ai_only', True) else ""),
              ""]
    return "\n".join(lines)


def write_markdown(report: dict, cfg) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / f"{report['date']}.md"
    path.write_text(markdown(report, cfg), "utf-8")
    (REPORTS / "latest.md").write_text(markdown(report, cfg), "utf-8")
    return path


# ---------------------------------------------------------------- Atom feed

def _html_table(report: dict) -> str:
    rows = "".join(
        f"<tr><td>{it['rank']}</td><td><a href=\"{html.escape(it['html_url'])}\">{html.escape(it['name'])}</a></td>"
        f"<td>{fmt_gain(it)}</td><td>{html.escape(it['change'])}</td><td>{html.escape(it.get('license') or '-')}</td>"
        f"<td>{html.escape(one_liner(it))}</td><td>{html.escape(caveat(it))}</td></tr>"
        for it in report["items"])
    return (f"<p>집계 기간: {_period(report)}</p><table><tr><th>순위</th><th>저장소</th><th>별 증가</th>"
            f"<th>지난주 대비</th><th>라이선스</th><th>한 줄</th><th>단, 확인할 것</th></tr>{rows}</table>")


def write_feed(cfg) -> Path:
    site = base_url(cfg)
    feed_url = f"{site}/github-rising/feed.xml" if site else "feed.xml"
    reports = list(reversed(all_reports(20)))
    updated = reports[0]["meta"]["until"] if reports else datetime.now().isoformat()
    entries = []
    for r in reports:
        link = f"{site}/github-rising/{r['date']}/" if site else f"{r['date']}/"
        entries.append(f"""  <entry>
    <id>tag:github-rising-tracker,{r['date']}</id>
    <title>{escape(title_for(r, cfg))}</title>
    <updated>{r['meta']['until']}</updated>
    <link href="{escape(link)}"/>
    <summary>{escape(', '.join(f"{it['rank']}. {it['name']} ({fmt_gain(it)})" for it in r['items'][:5]))}</summary>
    <content type="html">{escape(_html_table(r))}</content>
  </entry>""")
    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>{escape(cfg['github_rising']['report']['title_prefix'])} · 주간</title>
  <id>tag:github-rising-tracker,feed</id>
  <link rel="self" href="{escape(feed_url)}"/>
  <updated>{updated}</updated>
  <author><name>github-rising-tracker</name></author>
{chr(10).join(entries)}
</feed>
"""
    PUBLIC.mkdir(parents=True, exist_ok=True)
    path = PUBLIC / "feed.xml"
    path.write_text(xml, "utf-8")
    (PUBLIC / "latest.json").write_text(json.dumps(reports[0] if reports else {}, ensure_ascii=False, indent=1), "utf-8")
    return path


# ---------------------------------------------------------------- push notifications

def slack_payload(report: dict, cfg) -> dict:
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": title_for(report, cfg)[:150]}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": f"집계 {_period(report)} · GitHub API 직접 집계 (공식 트렌딩 아님)"}]},
        {"type": "divider"},
    ]
    for it in report["items"]:
        text = (f"*{it['rank']}. <{it['html_url']}|{it['name']}>*  ⭐ {fmt_gain(it)}  ·  {it['change']}\n"
                f"{one_liner(it)}\n_단, {caveat(it)}_")
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": text[:2900]}})
    if report["dropped"]:
        names = ", ".join(f"<{d['html_url']}|{d['name']}> (지난주 {d['prev_rank']}위)" for d in report["dropped"])
        blocks += [{"type": "divider"}, {"type": "section", "text": {"type": "mrkdwn", "text": f"*빠진 곳*: {names}"[:2900]}}]
    site = base_url(cfg)
    if site:
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": f"<{site}/github-rising/{report['date']}/|웹에서 전체 리포트 보기> · <{site}/github-rising/feed.xml|RSS>"}]})
    return {"text": title_for(report, cfg), "blocks": blocks[:50]}


def discord_payload(report: dict, cfg) -> dict:
    lines = [f"**{title_for(report, cfg)}**", f"-# 집계 {_period(report)}"]
    for it in report["items"]:
        lines.append(f"**{it['rank']}.** [{it['name']}](<{it['html_url']}>) ⭐ {fmt_gain(it)} · {it['change']} — {one_liner(it)}")
    content = "\n".join(lines)
    return {"content": content[:1990]}


def payloads(report: dict, cfg) -> dict:
    """Per-channel payloads for radar.notify.send()."""
    return {"slack": slack_payload(report, cfg), "discord": discord_payload(report, cfg),
            "generic_webhook": {"source": "github_rising", **report}}


# ---------------------------------------------------------------- GitHub Pages

def _chg_class(change: str) -> str:
    return "new" if change == "새로 진입" else "up" if "▲" in change else "down" if "▼" in change else ""


def report_html(report: dict, cfg) -> str:
    from ... import site
    e = site.esc
    items, dropped = report["items"], report["dropped"]
    rows = []
    for it in items:
        cav = e(it.get("caveat") or "")
        extra = []
        if it.get("suspicious"):
            extra.append('<span class="warn">⚠ 별 대비 포크가 아주 적어요 (가짜 스타 의심)</span>')
        if not it.get("license"):
            extra.append("라이선스 표기 없음")
        cav = " · ".join([c for c in [cav, *extra] if c]) or "-"
        meta = " · ".join(x for x in [it.get("language"), f"전체 ⭐ {it['stargazers_count']:,}"] if x)
        rows.append(
            f'<tr><td class="no">{it["rank"]}</td>'
            f'<td class="repo"><a href="{e(it["html_url"])}">{e(it["name"])}</a><div class="meta">{e(meta)}</div></td>'
            f'<td class="gain">{fmt_gain(it)}</td>'
            f'<td class="chg {_chg_class(it["change"])}" data-l="지난주 대비">{e(it["change"])}</td>'
            f'<td class="lic" data-l="라이선스">{e(it.get("license") or "-")}</td>'
            f'<td>{e(one_liner(it))}</td><td class="cav">{cav}</td></tr>')
    body = [f'<a class="back" href="../">← 모든 리포트</a>',
            f'<div class="meta">TOP 시리즈 · {e(report["date"])}</div>',
            f'<h1>{e(title_for(report, cfg))}</h1>',
            f'<div class="note">집계 기간: {e(_period(report))}. GitHub API로 별 수를 직접 세서 만든 순위예요. '
            'GitHub 공식 트렌딩 순위가 아니에요.'
            + (' 7일 전 기록이 없는 저장소는 별 누른 시각으로 셌고, <code>+N+</code>는 상한까지만 센 값이에요.'
               if any(it.get("method") == "stargazers" for it in items) else "")
            + (' 첫 주라 이번 주에 새로 생긴 저장소만 집계했어요. 다음 주부터 전체 후보를 집계해요.'
               if report["meta"].get("bootstrap_failed") else "") + '</div>',
            '<table class="rank"><thead><tr><th>순위</th><th>저장소</th><th>별 증가</th><th>지난주 대비</th>'
            '<th>라이선스</th><th>한 줄</th><th>단, 확인할 것</th></tr></thead><tbody>', *rows, '</tbody></table>']
    installs = [it for it in items if it.get("install")][:5]
    if installs:
        body.append('<h2>바로 써 보기 (설치 한 줄)</h2>')
        for it in installs:
            body.append(f'<p><b>{it["rank"]}위 {e(it["name"])}</b></p><pre><code>{e(it["install"])}</code></pre>')
    if dropped:
        body.append('<h2>빠진 곳</h2><ul class="plain">')
        for d in dropped:
            g = f" (이번 주 +{d['gain']:,})" if d.get("gain") is not None else ""
            body.append(f'<li><a href="{e(d["html_url"])}">{e(d["name"])}</a> · 지난주 {d["prev_rank"]}위{g}</li>')
        body.append("</ul>")
    f = cfg["github_rising"]["filter"]
    body.append('<h2>출처</h2><ul class="plain">'
                '<li>GitHub REST API: 검색, 저장소 정보, 별 기록(stargazers)</li>'
                f'<li>후보 {report["meta"]["candidates"]}개 중 별 증가 순. 필터: 포크 {f["min_forks"]}개 이상'
                + (", AI 관련 키워드" if f.get("ai_only", True) else "") + '</li>'
                '<li><a href="../feed.xml">RSS로 구독하기</a></li></ul>')
    return site.layout(title_for(report, cfg), "".join(body), 2,
                       ", ".join(f"{it['rank']}. {it['name']}" for it in items[:5]))


def _entries(cfg) -> list[dict]:
    return [{"date": r["date"], "slug": r["date"], "title": title_for(r, cfg),
             "href": f"github-rising/{r['date']}/",
             "preview": [f"{it['name']} {fmt_gain(it)}" for it in r["items"][:3]]}
            for r in reversed(all_reports(1000))]


def write_site(cfg) -> None:
    from ... import site
    for r in all_reports(1000):
        site.write(f"github-rising/{r['date']}/index.html", report_html(r, cfg))
    site.build_archive("github-rising", "GitHub 별 급상승 AI·개발 도구",
                       _entries(cfg), "매주 월요일, 지난 7일 동안 GitHub 별이 가장 많이 오른 저장소 10개예요.")


def site_section(cfg) -> dict:
    return {"label": "GitHub 별 급상승 (주간)", "href": "github-rising/", "entries": _entries(cfg)}
