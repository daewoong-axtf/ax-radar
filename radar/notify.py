"""Push channels shared by every source.

Each source returns {"slack": {...}, "discord": {...}, "generic_webhook": {...}}.
Webhook URLs come from env vars. A source-specific var wins over the shared one, e.g.
SLACK_WEBHOOK_URL_GITHUB_RISING (only this source) > SLACK_WEBHOOK_URL (all sources).
"""
from __future__ import annotations

import json
import os
import urllib.request

CHANNELS = {"slack": "SLACK_WEBHOOK_URL", "discord": "DISCORD_WEBHOOK_URL", "generic_webhook": "GENERIC_WEBHOOK_URL"}


def _post(url: str, payload: dict) -> int:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "ai-dev-radar"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status


def send(source: str, payloads: dict, cfg: dict, log=print) -> None:
    enabled = cfg.get("notify", {})
    for channel, env in CHANNELS.items():
        if channel not in payloads or not enabled.get(channel, True):
            continue
        url = os.environ.get(f"{env}_{source.upper()}") or os.environ.get(env)
        if not url:
            continue
        try:
            log(f"  {channel}: HTTP {_post(url, payloads[channel])}")
        except Exception as e:  # noqa: BLE001 - one channel failing must not stop the others
            log(f"  {channel}: failed ({e})")
