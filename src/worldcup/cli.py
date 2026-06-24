import argparse
from datetime import datetime, timezone, timedelta

from .fetcher import fetch_game_page
from .parser import html_to_text, parse_team_blocks
from .builder import build_snapshot, validate_snapshot, write_snapshot

_CST = timezone(timedelta(hours=8))


def _now_iso():
    return datetime.now(_CST).isoformat(timespec="seconds")


def main(argv=None):
    p = argparse.ArgumentParser(description="抓取世界杯球队近期战绩")
    p.add_argument("game_ids", nargs="+", help="球迷屋比赛 id,可多个")
    p.add_argument("--out", default="data/recent-form.json")
    p.add_argument("--schema", default="data/recent-form.schema.json")
    args = p.parse_args(argv)

    ts = _now_iso()
    by_key = {}
    for gid in args.game_ids:
        text = html_to_text(fetch_game_page(gid))
        for team in parse_team_blocks(text, updated_at=ts):
            by_key[team.team_id or team.name] = team

    snapshot = build_snapshot(list(by_key.values()), generated_at=ts)
    validate_snapshot(snapshot, args.schema)
    write_snapshot(snapshot, args.out)
    print(f"wrote {args.out} with {len(snapshot['teams'])} teams")


if __name__ == "__main__":
    main()
