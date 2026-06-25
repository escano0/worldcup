import argparse

from . import cli, odds, profile, recommend, squad, tournament


def main(argv=None):
    p = argparse.ArgumentParser(description="一键刷新全部 docs/ 数据")
    p.add_argument("--skip-odds", action="store_true", help="跳过盘口(无 API key 时)")
    p.add_argument("--skip-profiles", action="store_true", help="跳过 profile 聚合")
    args = p.parse_args(argv)

    steps = [
        ("teams", lambda: cli.main(["--all", "--docs-dir", "docs/teams"])),
        ("tournament", lambda: tournament.main(["--out", "docs/tournament.json"])),
        ("squad", lambda: squad.main(["--docs-dir", "docs/squads"])),
    ]
    if not args.skip_odds:
        steps.append(("odds", lambda: odds.main(["--out", "docs/odds.json"])))
    if not args.skip_profiles:
        steps.append(("profile", lambda: profile.main(["--docs-dir", "docs/profiles"])))
    if not args.skip_odds:  # 价值投注依赖盘口
        steps.append(("recommend", lambda: recommend.main(["--out", "docs/recommendations.json"])))

    results = {}
    for name, fn in steps:
        print(f"=== refresh: {name} ===")
        try:
            fn()
            results[name] = "ok"
        except SystemExit as e:
            results[name] = f"exit({e.code})"
        except Exception as e:  # 一步失败不影响其余步骤
            results[name] = f"error: {e}"
            print(f"  {name} failed: {e}")
    print("refresh summary:", results)


if __name__ == "__main__":
    main()
