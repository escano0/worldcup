import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

API_BASE = "https://api.the-odds-api.com/v4"
DEFAULT_SPORT = "soccer_fifa_world_cup"
KEY_FILE = Path(".odds_api_key")

_CST = timezone(timedelta(hours=8))


def _now_iso():
    return datetime.now(_CST).isoformat(timespec="seconds")


def _load_api_key(cli_key):
    """优先级:--api-key > 环境变量 ODDS_API_KEY > .odds_api_key 文件。"""
    if cli_key:
        return cli_key
    env = os.environ.get("ODDS_API_KEY")
    if env:
        return env
    if KEY_FILE.exists():
        return KEY_FILE.read_text(encoding="utf-8").strip()
    raise SystemExit(
        "缺少 Odds API key:用 --api-key、环境变量 ODDS_API_KEY 或 .odds_api_key 文件提供"
    )


def fetch_odds(api_key, *, sport=DEFAULT_SPORT, regions="eu,uk",
               markets="h2h,spreads,totals", odds_format="decimal",
               session=None, timeout=25):
    """从 The Odds API 拉取某项赛事的赔率,返回事件列表。"""
    sess = session or requests.Session()
    url = f"{API_BASE}/sports/{sport}/odds/"
    params = {
        "apiKey": api_key, "regions": regions,
        "markets": markets, "oddsFormat": odds_format,
    }
    resp = sess.get(url, params=params, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"odds API error {resp.status_code}: {resp.text[:200]}")
    return resp.json()


def _outcome(o):
    d = {"name": o["name"], "price": o["price"]}
    if "point" in o:
        d["point"] = o["point"]
    return d


def build_odds_doc(events, generated_at, *, sport, regions, markets):
    """把 The Odds API 事件列表整理成 docs/odds.json 结构(markets 按类型成 dict)。"""
    matches = []
    for e in events:
        books = []
        for b in e.get("bookmakers", []):
            mkts = {}
            for m in b.get("markets", []):
                mkts[m["key"]] = [_outcome(o) for o in m.get("outcomes", [])]
            books.append({
                "key": b.get("key"), "title": b.get("title"),
                "last_update": b.get("last_update"), "markets": mkts,
            })
        matches.append({
            "id": e.get("id"),
            "home": e.get("home_team"), "away": e.get("away_team"),
            "commence": e.get("commence_time"),
            "bookmakers": books,
        })
    return {
        "source": "the-odds-api", "sport": sport,
        "regions": regions, "markets": markets,
        "generated_at": generated_at,
        "match_count": len(matches), "matches": matches,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="拉取世界杯最新盘口/赔率 -> docs/odds.json")
    p.add_argument("--out", default="docs/odds.json")
    p.add_argument("--api-key", default=None, help="The Odds API key(默认读 env ODDS_API_KEY 或 .odds_api_key)")
    p.add_argument("--sport", default=DEFAULT_SPORT)
    p.add_argument("--regions", default="eu,uk")
    p.add_argument("--markets", default="h2h,spreads,totals")
    args = p.parse_args(argv)

    key = _load_api_key(args.api_key)
    events = fetch_odds(key, sport=args.sport, regions=args.regions, markets=args.markets)
    doc = build_odds_doc(events, _now_iso(), sport=args.sport,
                         regions=args.regions, markets=args.markets)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.out}: {doc['match_count']} matches, "
          f"markets={args.markets}, regions={args.regions}")


if __name__ == "__main__":
    main()
