from worldcup.models import MatchRecord, TeamForm

def test_match_record_defaults():
    m = MatchRecord(
        date="2026-06-19", competition="男足世界杯", opponent="波黑",
        is_home=True, gf=4, ga=1, result="W", home="瑞士", away="波黑", score="4-1",
    )
    assert m.match_id is None and m.note is None
    assert m.result == "W"

def test_team_form_defaults():
    t = TeamForm(
        name="瑞士",
        form={"played": 1, "w": 1, "d": 0, "l": 0, "gf": 4, "ga": 1, "win_rate": 1.0},
        recent=[], updated_at="2026-06-24T18:00:00+08:00",
    )
    assert t.team_id is None and t.name_en is None and t.rank is None and t.group is None
    assert t.recent == []
