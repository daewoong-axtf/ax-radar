"""Static GitHub Pages site shared by every source (public/)."""
from __future__ import annotations

import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"

CSS = """
:root{--bg:#fbfaf7;--surface:#fff;--text:#1d1d1f;--muted:#6b6b72;--line:#e7e4dc;--accent:#2f5bd3;
--accent-soft:#e9efff;--up:#1a7f4b;--down:#c0392b;--warn:#9a6400;--warn-soft:#fff4dc;--code:#f3f1ec}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#121214;--surface:#1b1b1f;--text:#ececf0;
--muted:#9a9aa3;--line:#2c2c33;--accent:#8aa8ff;--accent-soft:#1f2740;--up:#5bd193;--down:#ff8a7a;--warn:#f2c46b;
--warn-soft:#2e2615;--code:#24242a}}
:root[data-theme=dark]{--bg:#121214;--surface:#1b1b1f;--text:#ececf0;--muted:#9a9aa3;--line:#2c2c33;--accent:#8aa8ff;
--accent-soft:#1f2740;--up:#5bd193;--down:#ff8a7a;--warn:#f2c46b;--warn-soft:#2e2615;--code:#24242a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.65 "Noto Sans KR",system-ui,-apple-system,"Apple SD Gothic Neo",sans-serif;
-webkit-font-smoothing:antialiased;word-break:keep-all;overflow-wrap:anywhere}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:1080px;margin:0 auto;padding:0 16px}
header.top{border-bottom:1px solid var(--line);background:var(--surface)}
header.top .wrap{display:flex;align-items:center;gap:20px;height:56px}
.logo{font-weight:800;font-size:18px;color:var(--text);letter-spacing:-.02em}.logo span{color:var(--accent)}
nav{display:flex;gap:16px;font-size:14px;margin-left:auto}nav a{color:var(--muted)}
main{padding:32px 0 56px}
.meta{color:var(--muted);font-size:14px}
h1{font-size:clamp(24px,4vw,34px);line-height:1.3;letter-spacing:-.02em;margin:6px 0 16px}
h2{font-size:20px;margin:40px 0 12px;letter-spacing:-.01em}
.note{background:var(--accent-soft);border-radius:10px;padding:12px 16px;font-size:14px;color:var(--text)}
.back{font-size:14px;display:inline-block;margin-bottom:16px}
table.rank{width:100%;border-collapse:collapse;margin-top:20px;background:var(--surface);border:1px solid var(--line);
border-radius:12px;overflow:hidden;font-size:14.5px}
.rank th{text-align:left;font-weight:600;color:var(--muted);font-size:13px;padding:10px 12px;border-bottom:1px solid var(--line);white-space:nowrap}
.rank td{padding:12px;border-bottom:1px solid var(--line);vertical-align:top}
.rank tr:last-child td{border-bottom:0}
.rank .no{font-weight:800;font-size:18px;width:40px;text-align:center}
.rank .repo{min-width:220px}.rank .repo a{font-weight:600}
.rank .gain{font-weight:700;white-space:nowrap;font-variant-numeric:tabular-nums}
.chg{white-space:nowrap;font-size:13px}.chg.up{color:var(--up)}.chg.down{color:var(--down)}
.chg.new{color:var(--accent);font-weight:600}
.lic{font-size:12.5px;color:var(--muted);white-space:nowrap}
.cav{font-size:13.5px;color:var(--muted)}.warn{color:var(--warn);background:var(--warn-soft);border-radius:4px;padding:0 4px}
pre{background:var(--code);border-radius:8px;padding:12px 14px;overflow-x:auto;font-size:13.5px}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
ul.plain{padding-left:18px}
.cards{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));margin-top:12px}
.card{display:block;background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:16px;color:var(--text)}
.card:hover{border-color:var(--accent);text-decoration:none}
.card .t{font-weight:700;margin:4px 0 8px;line-height:1.4}
.card ol{margin:0;padding-left:20px;font-size:14px;color:var(--muted)}
.hero{font-size:17px;color:var(--muted);margin:0 0 8px}
.archive{list-style:none;padding:0;margin:0;border-top:1px solid var(--line)}
.archive li{display:flex;gap:12px;padding:10px 0;border-bottom:1px solid var(--line);font-size:15px}
.archive .d{color:var(--muted);font-variant-numeric:tabular-nums;white-space:nowrap}
footer{border-top:1px solid var(--line);color:var(--muted);font-size:13px;padding:20px 0 40px}
@media (max-width:720px){
 table.rank,.rank tbody,.rank tr,.rank td{display:block;width:100%}.rank thead{display:none}
 .rank tr{border-bottom:1px solid var(--line);padding:12px 4px;display:grid;grid-template-columns:36px 1fr;column-gap:8px}
 .rank td{border:0;padding:2px 0}.rank .no{grid-row:span 6;text-align:left;font-size:20px}
 .rank .gain::before{content:"⭐ "}.rank td[data-l]::before{content:attr(data-l) " · ";color:var(--muted);font-size:12px}
}
"""


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def layout(title: str, body: str, depth: int, description: str = "") -> str:
    up = "../" * depth
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(description)}">
<link rel="alternate" type="application/atom+xml" title="GitHub 별 급상승" href="{up}github-rising/feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<header class="top"><div class="wrap"><a class="logo" href="{up}">ax<span>·</span>radar</a>
<nav><a href="{up}">최신</a><a href="{up}github-rising/">GitHub 급상승</a><a href="{up}github-rising/feed.xml">RSS</a></nav></div></header>
<main><div class="wrap">{body}</div></main>
<footer><div class="wrap">ax-radar · AI·개발 동향 자동 수집 · 광고·협찬 아님 · 데이터는 GitHub API에서 직접 집계해요</div></footer>
</body></html>
"""


def write(rel: str, content: str) -> Path:
    path = PUBLIC / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, "utf-8")
    return path


def build_home(sections: list[dict]) -> Path:
    """sections: [{"label", "href", "entries": [{"date", "title", "href", "preview": [str]}]}] newest first."""
    body = ['<p class="hero">GitHub, 논문, 기술 블로그에서 AI·개발 동향을 모아 매주·매일 정리해요.</p>']
    for sec in sections:
        body.append(f'<h2><a href="{esc(sec["href"])}">{esc(sec["label"])}</a></h2>')
        if not sec["entries"]:
            body.append('<p class="meta">첫 리포트를 기다리는 중이에요.</p>')
            continue
        body.append('<div class="cards">')
        for e in sec["entries"][:3]:
            items = "".join(f"<li>{esc(p)}</li>" for p in e["preview"][:3])
            body.append(f'<a class="card" href="{esc(e["href"])}"><div class="meta">{esc(e["date"])}</div>'
                        f'<div class="t">{esc(e["title"])}</div><ol>{items}</ol></a>')
        body.append("</div>")
    return write("index.html", layout("ax-radar", "".join(body), 0, "AI·개발 동향 자동 수집"))


def build_archive(rel_dir: str, label: str, entries: list[dict], intro: str) -> Path:
    rows = "".join(f'<li><span class="d">{esc(e["date"])}</span><a href="{esc(e["slug"])}/">{esc(e["title"])}</a></li>'
                   for e in entries)
    body = (f'<h1>{esc(label)}</h1><p class="hero">{esc(intro)}</p>'
            f'<p class="meta"><a href="feed.xml">RSS로 구독하기</a></p>'
            f'<ul class="archive">{rows or "<li>아직 리포트가 없어요.</li>"}</ul>')
    return write(f"{rel_dir}/index.html", layout(label, body, 1, intro))
