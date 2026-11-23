"""Minimal GitHub REST client (stdlib only)."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"


class GitHubError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(f"GitHub {status}: {message}")
        self.status = status


class GitHub:
    def __init__(self, token: str | None = None, verbose: bool = False):
        self.token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        self.verbose = verbose
        self.calls = 0
        self._last_search = 0.0

    def _request(self, path: str, params: dict | None = None, accept: str = "application/vnd.github+json",
                 raw: bool = False):
        url = path if path.startswith("http") else API + path
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
        headers = {"Accept": accept, "User-Agent": "ai-dev-radar", "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        for attempt in range(5):
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    self.calls += 1
                    body = resp.read()
                    link = resp.headers.get("Link", "")
                    return (body.decode("utf-8", "replace") if raw else json.loads(body)), link
            except urllib.error.HTTPError as e:
                self.calls += 1
                msg = e.read().decode("utf-8", "replace")[:300]
                remaining = e.headers.get("X-RateLimit-Remaining")
                if e.code in (403, 429) and (remaining == "0" or "rate limit" in msg.lower()):
                    reset = int(e.headers.get("X-RateLimit-Reset", time.time() + 60))
                    wait = max(5, min(reset - time.time() + 2, 900))
                    if self.verbose:
                        print(f"  rate limited, sleeping {wait:.0f}s")
                    time.sleep(wait)
                    continue
                if e.code >= 500:
                    time.sleep(2 ** attempt)
                    continue
                raise GitHubError(e.code, msg) from None
            except (urllib.error.URLError, TimeoutError):
                time.sleep(2 ** attempt)
        raise GitHubError(0, f"giving up on {url}")

    def get(self, path: str, params: dict | None = None, **kw):
        return self._request(path, params, **kw)[0]

    def search_repos(self, q: str, pages: int = 1) -> list[dict]:
        items: list[dict] = []
        for page in range(1, pages + 1):
            # search API: 30 req/min with a token -> keep >=2.1s between calls
            gap = time.time() - self._last_search
            if gap < 2.1:
                time.sleep(2.1 - gap)
            self._last_search = time.time()
            data = self.get("/search/repositories", {"q": q, "sort": "stars", "order": "desc",
                                                    "per_page": 100, "page": page})
            items.extend(data.get("items", []))
            if len(data.get("items", [])) < 100:
                break
        return items

    def repo(self, full_name: str) -> dict:
        return self.get(f"/repos/{full_name}")

    def readme(self, full_name: str) -> str:
        try:
            return self._request(f"/repos/{full_name}/readme", accept="application/vnd.github.raw", raw=True)[0]
        except GitHubError:
            return ""

    def stargazer_page(self, full_name: str, page: int) -> list[dict]:
        return self.get(f"/repos/{full_name}/stargazers", {"per_page": 100, "page": page},
                        accept="application/vnd.github.star+json")
