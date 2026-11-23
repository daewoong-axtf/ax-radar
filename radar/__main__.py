"""CLI: python -m radar <source> <command> [--no-notify] [--dry-run] [--fresh]

예: python -m radar github_rising report
"""
from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

from . import notify, site
from .github import GitHub
from .sources import github_rising

ROOT = Path(__file__).resolve().parent.parent

# 새 소스는 여기에 등록해요. 모듈은 COMMANDS 와 run(command, cfg, gh, args, log) 를 가져야 해요.
SOURCES = {"github_rising": github_rising}


def load_cfg(path: str) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="radar", description="AI·개발 동향 수집 + 알림 봇")
    p.add_argument("source", choices=sorted(SOURCES))
    p.add_argument("command")
    p.add_argument("--config", default=str(ROOT / "config.toml"))
    p.add_argument("--no-notify", action="store_true", help="Slack/Discord/웹훅 전송 안 함")
    p.add_argument("--dry-run", action="store_true", help="파일 저장·전송 없이 결과만 출력")
    p.add_argument("--fresh", action="store_true", help="오늘 수집분이 있어도 새로 수집")
    p.add_argument("--file", help="enrich: 요약 JSON 파일 경로")
    args = p.parse_args(argv)
    mod = SOURCES[args.source]
    if args.command not in mod.COMMANDS:
        p.error(f"{args.source} commands: {', '.join(mod.COMMANDS)}")
    cfg = load_cfg(args.config)
    result = mod.run(args.command, cfg, GitHub(verbose=True), args)
    if not args.dry_run and args.command not in ("snapshot", "pending"):
        site.build_home([m.site_section(cfg) for m in SOURCES.values() if hasattr(m, "site_section")])
    if result and not args.no_notify:
        notify.send(args.source, result["payloads"], cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
