import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

_CST = timezone(timedelta(hours=8))


def _now_iso():
    return datetime.now(_CST).isoformat(timespec="seconds")


def build_profile(slug, team_form, squad, standing, generated_at):
    """合并某队的战绩 + 阵容 + 小组积分为单份 profile。"""
    return {
        "team_id": slug,
        "name": team_form.get("name") or squad.get("name"),
        "name_en": team_form.get("name_en"),
        "group": squad.get("group") or team_form.get("group"),
        "standing": standing,
        "form": team_form.get("form"),
        "recent": team_form.get("recent", []),
        "coach": squad.get("coach"),
        "squad_updated": squad.get("squad_updated"),
        "formation": squad.get("formation"),
        "player_count": squad.get("player_count"),
        "squad": squad.get("squad", {}),
        "injuries": squad.get("injuries", []),
        "generated_at": generated_at,
    }


def _load(path):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def main(argv=None):
    p = argparse.ArgumentParser(description="合并各队战绩+阵容+积分 -> docs/profiles/{slug}.json")
    p.add_argument("--docs-dir", default="docs/profiles")
    p.add_argument("--teams-dir", default="docs/teams")
    p.add_argument("--squads-dir", default="docs/squads")
    p.add_argument("--tournament", default="docs/tournament.json")
    args = p.parse_args(argv)

    ts = _now_iso()
    # slug -> 积分(含组)
    standing_by_slug = {}
    tour = _load(args.tournament)
    if tour:
        for g in tour.get("groups", []):
            for t in g.get("standings", []):
                standing_by_slug[t["slug"]] = {
                    "rank": t.get("rank"), "w": t.get("w"), "d": t.get("d"),
                    "l": t.get("l"), "points": t.get("points"), "zone": t.get("zone"),
                }

    out_dir = Path(args.docs_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    squads_dir = Path(args.squads_dir)
    teams_dir = Path(args.teams_dir)

    written = 0
    for sq_file in sorted(squads_dir.glob("*.json")):
        slug = sq_file.stem
        squad = json.loads(sq_file.read_text(encoding="utf-8"))
        team_form = _load(teams_dir / f"{slug}.json") or {}
        prof = build_profile(slug, team_form, squad,
                             standing_by_slug.get(slug), ts)
        (out_dir / f"{slug}.json").write_text(
            json.dumps(prof, ensure_ascii=False, indent=2), encoding="utf-8")
        written += 1

    print(f"wrote {written} profiles to {args.docs_dir}")


if __name__ == "__main__":
    main()
