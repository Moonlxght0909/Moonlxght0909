#!/usr/bin/env python3
"""Refresh profile repository highlights and an optional AI-generated daily brief."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from pathlib import Path

USERNAME = os.getenv("GITHUB_USERNAME", "Moonlxght0909")
TOKEN = os.getenv("GITHUB_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
README = Path("README.md")


def get_json(url: str, headers: dict[str, str]) -> object:
    request = Request(url, headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Moonlxght0909-Daily-Profile-Updater",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    return headers


def fetch_repositories() -> list[dict]:
    url = (
        f"https://api.github.com/users/{USERNAME}/repos"
        "?type=owner&sort=updated&per_page=100"
    )
    data = get_json(url, github_headers())
    if not isinstance(data, list):
        raise RuntimeError("Unexpected GitHub API response for repositories.")
    # Skip forks and profile repository; keep projects owned by the account.
    repos = [
        repo for repo in data
        if not repo.get("fork") and repo.get("name", "").lower() != USERNAME.lower()
    ]
    return repos[:6]


def repo_section(repos: list[dict], generated: str) -> str:
    if not repos:
        return f"_No public repositories were returned by the GitHub API as of {generated}_"
    lines = [f"_Automatically refreshed: {generated} UTC_", ""]
    for repo in repos:
        name = repo.get("name", "Repository")
        url = repo.get("html_url", f"https://github.com/{USERNAME}")
        description = repo.get("description") or "No description provided yet."
        language = repo.get("language") or "Not specified"
        stars = repo.get("stargazers_count", 0)
        lines.extend([
            f"### [{name}]({url})",
            description.replace("\n", " "),
            "",
            f"`{language}` · ⭐ {stars} · [Source]( {url} )",
            "",
        ])
    return "\n".join(lines).strip()


def fetch_recent_activity(repos: list[dict]) -> list[dict]:
    activity = []
    headers = github_headers()
    for repo in repos[:5]:
        full_name = repo.get("full_name")
        if not full_name:
            continue
        url = f"https://api.github.com/repos/{full_name}/commits?per_page=3"
        try:
            commits = get_json(url, headers)
        except (HTTPError, URLError, TimeoutError):
            continue
        if not isinstance(commits, list):
            continue
        for item in commits[:3]:
            commit = item.get("commit", {})
            message = (commit.get("message") or "").splitlines()[0][:180]
            author = commit.get("author") or {}
            activity.append({
                "repository": full_name,
                "message": message,
                "date": author.get("date", ""),
                "url": item.get("html_url", ""),
            })
    return activity[:12]


def openai_brief(repos: list[dict], activity: list[dict], generated: str) -> str | None:
    if not OPENAI_API_KEY:
        print("OPENAI_API_KEY is not configured; keeping AI brief placeholder.")
        return None

    safe_repos = [{
        "name": r.get("name"),
        "description": r.get("description"),
        "language": r.get("language"),
        "updated_at": r.get("updated_at"),
        "stars": r.get("stargazers_count"),
        "url": r.get("html_url"),
    } for r in repos]

    prompt = {
        "profile": USERNAME,
        "generated_at_utc": generated,
        "public_repositories": safe_repos,
        "recent_commits": activity,
        "task": (
            "Write a concise, polished GitHub profile daily brief in Markdown, "
            "in English. Use ONLY the supplied facts. Do not invent projects, "
            "skills, accomplishments, commit activity, or future plans. If there "
            "is no recent commit data, say that no recent public commit data was "
            "available; do not imply the developer was inactive. Include a short "
            "activity snapshot and one practical developer takeaway. Keep it "
            "under 140 words. Do not include a heading because the README already "
            "has one. Do not mention private data."
        ),
    }

    payload = {
        "model": OPENAI_MODEL,
        "input": [
            {
                "role": "system",
                "content": "You write factual, restrained developer profile updates."
            },
            {
                "role": "user",
                "content": json.dumps(prompt, ensure_ascii=False)
            }
        ],
        "max_output_tokens": 250,
    }
    request = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"OpenAI API returned HTTP {exc.code}: {detail}") from exc

    # Responses API output text extraction.
    chunks = []
    for item in result.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                chunks.append(content["text"])
    text = "\n".join(chunks).strip()
    return text or None


def replace_section(content: str, start: str, end: str, replacement: str) -> str:
    if start not in content or end not in content:
        raise RuntimeError(f"README markers not found: {start} / {end}")
    before, remainder = content.split(start, 1)
    _, after = remainder.split(end, 1)
    return f"{before}{start}\n{replacement.strip()}\n{end}{after}"


def main() -> int:
    if not README.exists():
        raise RuntimeError("README.md was not found. Run this script from repository root.")

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    repos = fetch_repositories()
    activity = fetch_recent_activity(repos)

    content = README.read_text(encoding="utf-8")
    content = replace_section(
        content, "<!-- REPOS:START -->", "<!-- REPOS:END -->",
        repo_section(repos, generated),
    )

    brief = openai_brief(repos, activity, generated)
    if brief:
        brief = f"{brief}\n\n<sub>AI-generated from public GitHub repository and commit metadata · Updated {generated} UTC</sub>"
        content = replace_section(
            content, "<!-- AI-BRIEF:START -->", "<!-- AI-BRIEF:END -->", brief
        )
    else:
        # Still record that the automation ran, without pretending AI ran.
        fallback = (
            f"_Automation ran on {generated} UTC. Add the `OPENAI_API_KEY` "
            "repository secret to enable the AI-generated daily brief._"
        )
        content = replace_section(
            content, "<!-- AI-BRIEF:START -->", "<!-- AI-BRIEF:END -->", fallback
        )

    README.write_text(content, encoding="utf-8")
    print(f"Updated README.md with {len(repos)} repository entries.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (HTTPError, URLError, TimeoutError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
