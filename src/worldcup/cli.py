import argparse
import time
from datetime import datetime, timezone, timedelta

from .fetcher import fetch_game_page
from .parser import html_to_text, parse_team_blocks, parse_team_slugs
from .builder import build_snapshot, validate_snapshot, write_snapshot, write_team_files
from .schedule import fetch_schedule_html, parse_game_ids

_CST = timezone(timedelta(hours=8))


def _now_iso():
    return datetime.now(_CST).isoformat(timespec="seconds")


def main(argv=None):
    p = argparse.ArgumentParser(description="抓取世界杯球队近期战绩")
    p.add_argument("game_ids", nargs="*", help="球迷屋比赛 id,可多个")
    p.add_argument("--out", default=None, help="可选:额外写一个聚合 JSON 快照")
    p.add_argument("--schema", default="data/recent-form.schema.json")
    p.add_argument("--all", action="store_true", help="从世界杯赛程页枚举全部比赛 id")
    p.add_argument("--delay", type=float, default=0.5, help="批量抓取每场之间的间隔秒数")
    p.add_argument("--docs-dir", default="docs/teams", help="每队一个 JSON 文件的输出目录")
    args = p.parse_args(argv)

    ts = _now_iso()

    game_ids = list(args.game_ids)
    if args.all:
        game_ids += parse_game_ids(fetch_schedule_html())
    game_ids = list(dict.fromkeys(game_ids))  # 去重保序
    if not game_ids:
        p.error("需要至少一个 game id,或使用 --all 从赛程页枚举")

    by_key = {}
    failed = []
    for i, gid in enumerate(game_ids):
        if i > 0 and args.delay > 0:
            time.sleep(args.delay)
        try:
            html = fetch_game_page(gid)
            slug_map = parse_team_slugs(html)
            for team in parse_team_blocks(html_to_text(html), updated_at=ts):
                team.team_id = slug_map.get(team.name)
                by_key[team.team_id or team.name] = team
        except Exception as e:  # 单场失败(如未开赛/无战绩)跳过,不中断批量
            failed.append(gid)
            print(f"skip {gid}: {e}")

    snapshot = build_snapshot(list(by_key.values()), generated_at=ts)
    validate_snapshot(snapshot, args.schema)

    n = write_team_files(by_key.values(), args.docs_dir)
    msg = f"wrote {n} team files to {args.docs_dir} from {len(game_ids)} games"
    if failed:
        msg += f" ({len(failed)} skipped)"
    print(msg)

    if args.out:
        write_snapshot(snapshot, args.out)
        print(f"also wrote aggregate {args.out}")

    # 全部比赛都失败 → 非0退出,便于自动化区分"个别未开赛"与"整体抓取崩了"
    if game_ids and len(failed) == len(game_ids):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
