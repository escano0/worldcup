import pytest
from worldcup.parser import parse_score, compute_result, build_match_record

def test_parse_score_with_spaces():
    assert parse_score("4 - 1") == (4, 1)
    assert parse_score("0-0") == (0, 0)

def test_parse_score_invalid():
    with pytest.raises(ValueError):
        parse_score("待定")

def test_compute_result():
    assert compute_result(4, 1) == "W"
    assert compute_result(1, 1) == "D"
    assert compute_result(0, 2) == "L"

def test_build_match_record_team_is_home():
    m = build_match_record("瑞士", "2026-06-19", "男足世界杯", "瑞士", 4, 1, "波黑")
    assert m.is_home is True and m.opponent == "波黑"
    assert m.gf == 4 and m.ga == 1 and m.result == "W" and m.score == "4-1"

def test_build_match_record_team_is_away():
    m = build_match_record("瑞士", "2026-06-14", "男足世界杯", "卡塔尔", 1, 1, "瑞士")
    assert m.is_home is False and m.opponent == "卡塔尔"
    assert m.gf == 1 and m.ga == 1 and m.result == "D" and m.score == "1-1"

def test_build_match_record_unknown_team_raises():
    with pytest.raises(ValueError):
        build_match_record("瑞士", "2026-06-14", "国际赛", "法国", 2, 0, "德国")


from pathlib import Path
from worldcup.parser import html_to_text, parse_team_blocks

FIXTURE = Path("tests/fixtures/recent_form_sample.html").read_text(encoding="utf-8")

def test_html_to_text_strips_scripts_and_tags():
    text = html_to_text(FIXTURE)
    assert "最近战绩" in text and "男足世界杯" in text
    assert "<div" not in text
    assert "伪造" not in text  # script 内容被剔除

def test_parse_team_blocks_two_teams():
    teams = parse_team_blocks(html_to_text(FIXTURE), updated_at="2026-06-24T18:00:00+08:00")
    names = {t.name for t in teams}
    assert names == {"瑞士", "加拿大"}

def test_parse_team_blocks_switzerland_form_and_rows():
    teams = {t.name: t for t in parse_team_blocks(html_to_text(FIXTURE), updated_at="T")}
    sui = teams["瑞士"]
    assert sui.form == {"played": 10, "w": 4, "d": 5, "l": 1, "gf": 20, "ga": 10, "win_rate": 0.4}
    assert len(sui.recent) == 10
    m0, m1 = sui.recent[0], sui.recent[1]
    assert (m0.opponent, m0.is_home, m0.gf, m0.ga, m0.result) == ("波黑", True, 4, 1, "W")
    assert (m1.opponent, m1.is_home, m1.gf, m1.ga, m1.result) == ("卡塔尔", False, 1, 1, "D")
    assert sui.updated_at == "T"


def test_parse_team_blocks_multi_token_competition():
    # 多词赛事名(中间有空格)应被正确解析到 competition,而非丢行
    text = ("最近战绩 法国 进球3/失球0/胜率100.0% 1胜 0平 0负 "
            "2026-06-19 国际 友谊赛 法国 3 - 0 德国")
    teams = parse_team_blocks(text, updated_at="T")
    assert len(teams) == 1
    m = teams[0].recent[0]
    assert m.competition == "国际 友谊赛"
    assert m.opponent == "德国" and m.is_home is True
    assert m.gf == 3 and m.ga == 0 and m.result == "W"


def test_parse_team_blocks_count_mismatch_raises():
    # header 声称 2 场(1胜1平)但只给了 1 行 -> 必须报错,而非静默
    text = ("最近战绩 法国 进球3/失球0/胜率50.0% 1胜 1平 0负 "
            "2026-06-19 世预 法国 3 - 0 德国")
    with pytest.raises(ValueError):
        parse_team_blocks(text, updated_at="T")
