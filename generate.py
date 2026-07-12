#!/usr/bin/env python3
"""Generate dark_mode.svg / light_mode.svg for the GitHub profile README.

ASCII face (face.txt) on the left, neofetch-style live stats on the right.
Uses only the Python standard library. Auth via GITHUB_TOKEN env var.
"""

import json
import os
import urllib.request
from datetime import datetime, date, timezone

USERNAME = "isaaclins"
BIRTHDAY = date(2007, 3, 28)
API_URL = "https://api.github.com/graphql"

LINE_HEIGHT = 20
FONT_SIZE = 16
CHAR_WIDTH = 9.6
PADDING = 25
GAP = 40

THEMES = {
    "dark_mode.svg": {
        "bg": "#161b22", "fg": "#c9d1d9", "key": "#ffa657",
        "value": "#a5d6ff", "accent": "#3fb950", "dim": "#616e7f",
    },
    "light_mode.svg": {
        "bg": "#fffefe", "fg": "#24292f", "key": "#953800",
        "value": "#0a3069", "accent": "#1a7f37", "dim": "#57606a",
    },
}


def graphql(query: str) -> dict:
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        API_URL,
        data=json.dumps({"query": query}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as res:
        payload = json.loads(res.read())
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]


def fetch_stats() -> dict:
    user = graphql(f'''
    query {{
      user(login: "{USERNAME}") {{
        createdAt
        followers {{ totalCount }}
        repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC) {{
          totalCount
          nodes {{ stargazerCount }}
        }}
        repositoriesContributedTo(first: 1, contributionTypes: [COMMIT, PULL_REQUEST]) {{ totalCount }}
      }}
    }}''')["user"]

    created_year = datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00")).year
    current_year = datetime.now(timezone.utc).year
    total_commits = 0
    for year in range(created_year, current_year + 1):
        start = f"{year}-01-01T00:00:00Z"
        end = f"{year}-12-31T23:59:59Z"
        contributions = graphql(f'''
        query {{
          user(login: "{USERNAME}") {{
            contributionsCollection(from: "{start}", to: "{end}") {{
              totalCommitContributions
            }}
          }}
        }}''')["user"]["contributionsCollection"]
        total_commits += contributions["totalCommitContributions"]

    return {
        "repos": user["repositories"]["totalCount"],
        "contributed": user["repositoriesContributedTo"]["totalCount"],
        "stars": sum(n["stargazerCount"] for n in user["repositories"]["nodes"]),
        "followers": user["followers"]["totalCount"],
        "commits": total_commits,
    }


def uptime() -> str:
    today = date.today()
    years = today.year - BIRTHDAY.year - ((today.month, today.day) < (BIRTHDAY.month, BIRTHDAY.day))
    anniversary = date(BIRTHDAY.year + years, BIRTHDAY.month, BIRTHDAY.day)
    months = (today.year - anniversary.year) * 12 + today.month - anniversary.month
    if today.day < anniversary.day:
        months -= 1
    month_anchor_month = (anniversary.month - 1 + months) % 12 + 1
    month_anchor_year = anniversary.year + (anniversary.month - 1 + months) // 12
    days = (today - date(month_anchor_year, month_anchor_month, min(anniversary.day, 28))).days
    return f"{years} years, {months} months, {days} days"


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def stat_lines(stats: dict) -> list:
    # (key, value) pairs; key=None renders the whole line in fg color.
    return [
        (None, f"{USERNAME}@github"),
        (None, "-" * 24),
        ("OS", "macOS arm64"),
        ("Uptime", uptime()),
        ("Host", "Swisscom AG · Security"),
        ("Shell", "fish + ghostty"),
        ("Editor", "pi coding agent"),
        ("Location", "Zürich, Switzerland"),
        ("Blog", "isaaclins.com"),
        ("Contact", "contact@isaaclins.com"),
        (None, ""),
        ("Repos", f"{stats['repos']} public · contributed to {stats['contributed']}"),
        ("Commits", f"{stats['commits']:,}"),
        ("Stars", f"{stats['stars']}"),
        ("Followers", f"{stats['followers']}"),
        (None, ""),
        (None, f"generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"),
    ]


def build_svg(face: list, stats: dict, theme: dict) -> str:
    face_width_chars = max((len(line) for line in face), default=0)
    stats_x = PADDING + int(face_width_chars * CHAR_WIDTH) + GAP
    lines = stat_lines(stats)
    rows = max(len(face), len(lines))
    height = PADDING * 2 + rows * LINE_HEIGHT
    width = stats_x + 480

    parts = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        f'<svg xmlns="http://www.w3.org/2000/svg" font-family="Menlo,Consolas,monospace" '
        f'width="{width}px" height="{height}px" font-size="{FONT_SIZE}px">',
        f'<rect width="{width}px" height="{height}px" fill="{theme["bg"]}" rx="15"/>',
    ]

    y = PADDING + LINE_HEIGHT
    face_svg = [f'<text fill="{theme["accent"]}">']
    for line in face:
        face_svg.append(f'<tspan x="{PADDING}" y="{y}">{esc(line)}</tspan>')
        y += LINE_HEIGHT
    face_svg.append("</text>")
    parts.extend(face_svg)

    y = PADDING + LINE_HEIGHT
    for key, value in lines:
        if key is None:
            if value:
                parts.append(f'<text x="{stats_x}" y="{y}" fill="{theme["fg"]}" font-weight="bold">{esc(value)}</text>')
        else:
            parts.append(
                f'<text x="{stats_x}" y="{y}"><tspan fill="{theme["key"]}">{esc(key)}</tspan>'
                f'<tspan fill="{theme["dim"]}">: </tspan>'
                f'<tspan fill="{theme["value"]}">{esc(value)}</tspan></text>'
            )
        y += LINE_HEIGHT

    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(repo_dir, "face.txt"), encoding="utf-8") as f:
        face = [line.rstrip("\n") for line in f.read().rstrip("\n").split("\n")]

    stats = fetch_stats()
    for filename, theme in THEMES.items():
        svg = build_svg(face, stats, theme)
        with open(os.path.join(repo_dir, filename), "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"wrote {filename}")


if __name__ == "__main__":
    main()
