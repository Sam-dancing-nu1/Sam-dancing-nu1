# -*- coding: utf-8 -*-
"""transform_stats.py — 把 GitHub GraphQL 原始响应整形为 data/stats.json。
用法: python transform_stats.py <raw.json> [out_dir]
校验失败直接退出非 0（Actions 侧不会覆写旧数据）。
"""
import json
import os
import sys
from datetime import datetime, timezone

LEVEL = {
    "NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4,
}

def main():
    raw_path = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    with open(raw_path, encoding="utf-8") as f:
        raw = json.load(f)

    user = (raw.get("data") or {}).get("user")
    if not user:
        print("FATAL: no user in response (auth/rate-limit?)")
        sys.exit(1)
    cal = ((user.get("contributionsCollection") or {}).get("contributionCalendar") or {})
    total = cal.get("totalContributions")
    weeks = cal.get("weeks") or []
    if not isinstance(total, int) or not weeks:
        print("FATAL: contributionCalendar invalid")
        sys.exit(1)

    repos = [r for r in (user.get("repositories") or {}).get("nodes") or []
             if not r.get("isFork") and not r.get("isArchived")]  # star/仓库计数排除 fork
    all_repos = (user.get("repositories") or {}).get("nodes") or []  # 语言分布含 fork（用户确认照实）

    lang = {}
    for r in all_repos:
        for e in (r.get("languages") or {}).get("edges") or []:
            name = e["node"]["name"]
            size = int(e["size"])
            acc = lang.setdefault(name, {"name": name, "color": e["node"].get("color") or "#8A90A0", "size": 0})
            acc["size"] += size
    languages = sorted(lang.values(), key=lambda x: -x["size"])[:8]

    stats = {
        "schema": 1,
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "login": user["login"],
        "name": user.get("name"),
        "url": user["url"],
        "avatarUrl": user.get("avatarUrl", ""),
        "followers": user["followers"]["totalCount"],
        "following": user["following"]["totalCount"],
        "publicRepos": user["repositories"]["totalCount"],
        "stars": sum(r["stargazerCount"] for r in repos),
        "contributions": {
            "total": total,
            "weeks": [
                {"days": [
                    {"d": d["date"], "c": d["contributionCount"],
                     "l": LEVEL.get(d["contributionLevel"], 0)}
                    for d in w.get("contributionDays") or []
                ]} for w in weeks
            ],
        },
        "languages": [{"name": l["name"], "color": l["color"], "size": l["size"]} for l in languages],
        "repos": [{"name": r["name"], "url": r["url"], "stars": r["stargazerCount"]}
                  for r in sorted(repos, key=lambda x: -x["stargazerCount"])[:8]],
    }

    # 产物二次校验
    assert isinstance(stats["stars"], int) and isinstance(stats["contributions"]["total"], int)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "stats.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=1)
    print("wrote", out, "| total=%d stars=%d repos=%d langs=%d"
          % (stats["contributions"]["total"], stats["stars"], stats["publicRepos"], len(languages)))

if __name__ == "__main__":
    main()
