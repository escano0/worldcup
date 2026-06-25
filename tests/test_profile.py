import json
from worldcup.profile import build_profile, main


def test_build_profile_merges_sources():
    team_form = {"name": "瑞士", "name_en": "Switzerland", "group": "B",
                 "form": {"played": 10, "w": 4, "d": 5, "l": 1, "gf": 20, "ga": 10, "win_rate": 0.4},
                 "recent": [{"date": "2026-06-19", "opponent": "波黑", "result": "W"}]}
    squad = {"name": "瑞士", "group": "B", "coach": "X", "squad_updated": "2026/6/10",
             "formation": None, "player_count": 26,
             "squad": {"前锋": [{"name": "恩博洛", "number": 7}]}, "injuries": []}
    standing = {"rank": 2, "w": 1, "d": 1, "l": 1, "points": 4, "zone": "晋级32强"}
    p = build_profile("ruishi", team_form, squad, standing, "2026-06-25T12:00:00+08:00")
    assert p["team_id"] == "ruishi" and p["name"] == "瑞士" and p["name_en"] == "Switzerland"
    assert p["group"] == "B"
    assert p["standing"] == standing
    assert p["form"]["w"] == 4 and p["recent"][0]["result"] == "W"
    assert p["coach"] == "X" and p["player_count"] == 26
    assert p["squad"]["前锋"][0]["name"] == "恩博洛"
    assert p["injuries"] == []
    assert p["generated_at"] == "2026-06-25T12:00:00+08:00"


def test_build_profile_tolerates_missing_standing_and_form():
    squad = {"name": "海地", "group": "C", "coach": None, "squad_updated": None,
             "formation": None, "player_count": 0, "squad": {}, "injuries": []}
    p = build_profile("haidi", {}, squad, None, "T")
    assert p["team_id"] == "haidi" and p["name"] == "海地"
    assert p["standing"] is None and p["form"] is None and p["recent"] == []


def test_main_writes_profiles(tmp_path):
    teams = tmp_path / "teams"; squads = tmp_path / "squads"; profiles = tmp_path / "profiles"
    teams.mkdir(); squads.mkdir()
    (teams / "ruishi.json").write_text(json.dumps({
        "name": "瑞士", "name_en": "Switzerland", "group": "B",
        "form": {"w": 4}, "recent": [{"result": "W"}]}), encoding="utf-8")
    (squads / "ruishi.json").write_text(json.dumps({
        "name": "瑞士", "group": "B", "coach": "X", "player_count": 26,
        "squad": {"前锋": []}, "injuries": [], "formation": None, "squad_updated": "u"}), encoding="utf-8")
    tjson = tmp_path / "tournament.json"
    tjson.write_text(json.dumps({"groups": [
        {"group": "B", "standings": [
            {"rank": 2, "team": "瑞士", "slug": "ruishi", "w": 1, "d": 1, "l": 1, "points": 4, "zone": "晋级32强"}]}]}),
        encoding="utf-8")
    main(["--docs-dir", str(profiles), "--teams-dir", str(teams),
          "--squads-dir", str(squads), "--tournament", str(tjson)])
    out = json.loads((profiles / "ruishi.json").read_text(encoding="utf-8"))
    assert out["team_id"] == "ruishi" and out["coach"] == "X"
    assert out["standing"]["points"] == 4 and out["form"]["w"] == 4
