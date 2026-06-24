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
