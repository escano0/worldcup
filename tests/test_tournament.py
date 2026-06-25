from worldcup.tournament import (
    parse_standings, parse_schedule_matches, build_tournament, BRACKET_SKELETON,
)

STANDINGS_HTML = (
    '<a href="/team/moxige1">墨西哥</a><a href="/team/hanguo1">韩国</a>'
    '<a href="/team/jieke1">捷克</a><a href="/team/nanfei">南非</a>'
    '<a href="/team/jianada1">加拿大</a><a href="/team/ruishi">瑞士</a>'
    '<div>积分榜 排名 球队 胜/平/负 积分 晋级32强 '
    '1 墨西哥 2 / 0 / 0 6 2 韩国 1 / 0 / 1 3 晋级待定 3 捷克 0 / 1 / 1 1 4 南非 0 / 1 / 1 1 '
    '1 加拿大 1 / 1 / 0 4 2 瑞士 1 / 1 / 0 4 晋级待定 3 波黑 0 / 1 / 1 1 4 卡塔尔 0 / 0 / 2 0</div>'
)

SCHED_HTML = (
    '<a href="/game/100000000001">x</a><a href="/game/100000000002">y</a>'
    '<div>今天 06-25 星期四 (1场) '
    'B组 第3轮 小组赛 03:00 完场 瑞士 2 - 1 加拿大 0 - 0 数据 回放 '
    '明天 06-26 星期五 (1场) '
    'E组 第3轮 小组赛 04:00 未开赛 厄瓜多尔 VS 德国 - 前瞻</div>'
)


def test_parse_standings_groups_and_fields():
    groups = parse_standings(STANDINGS_HTML)
    assert len(groups) == 2
    a = groups[0]
    assert a["group"] == "A"
    assert [t["team"] for t in a["standings"]] == ["墨西哥", "韩国", "捷克", "南非"]
    mex = a["standings"][0]
    assert mex == {"rank": 1, "team": "墨西哥", "slug": "moxige1",
                   "w": 2, "d": 0, "l": 0, "points": 6, "zone": "晋级32强"}
    assert a["standings"][2]["zone"] == "晋级待定"   # rank 3
    assert groups[1]["group"] == "B"
    assert groups[1]["standings"][0]["team"] == "加拿大"


def test_parse_schedule_matches_finished_and_upcoming():
    ms = parse_schedule_matches(SCHED_HTML)
    assert len(ms) == 2
    fin = ms[0]
    assert fin["stage"] == "group" and fin["group"] == "B" and fin["round"] == 3
    assert fin["date"] == "2026-06-25" and fin["time"] == "03:00"
    assert fin["status"] == "finished" and fin["home"] == "瑞士" and fin["away"] == "加拿大"
    assert fin["score"] == "2-1" and fin["ht"] == "0-0"
    assert fin["game_id"] == "100000000001"
    up = ms[1]
    assert up["status"] == "scheduled" and up["date"] == "2026-06-26"
    assert up["home"] == "厄瓜多尔" and up["away"] == "德国"
    assert up["score"] is None and up["game_id"] == "100000000002"


def test_build_tournament_assembles_with_bracket_skeleton():
    groups = parse_standings(STANDINGS_HTML)
    matches = parse_schedule_matches(SCHED_HTML)
    doc = build_tournament(groups, matches, "2026-06-25T12:00:00+08:00")
    assert doc["tournament"] == "2026-world-cup"
    assert doc["generated_at"] == "2026-06-25T12:00:00+08:00"
    assert doc["groups"] == groups and doc["matches"] == matches
    assert [b["stage"] for b in doc["bracket"]] == [s for s, _ in BRACKET_SKELETON]
    assert all(b["matches"] == [] for b in doc["bracket"])     # knockout TBD
    r32 = doc["bracket"][0]
    assert r32["stage"] == "round_of_32" and r32["slots"] == 16


def test_main_writes_tournament_json(monkeypatch, tmp_path):
    import json
    import worldcup.tournament as T
    monkeypatch.setattr(T, "fetch_schedule_html", lambda **kw: SCHED_HTML)
    monkeypatch.setattr(T, "fetch_game_page", lambda gid, **kw: STANDINGS_HTML)
    out = tmp_path / "tournament.json"
    T.main(["--out", str(out)])
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["tournament"] == "2026-world-cup"
    assert len(doc["groups"]) == 2          # from STANDINGS_HTML
    assert len(doc["matches"]) == 2         # from SCHED_HTML
    assert doc["bracket"][0]["stage"] == "round_of_32"
    assert doc["generated_at"]               # non-empty timestamp
