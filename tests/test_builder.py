import json
from pathlib import Path
import jsonschema
from worldcup.parser import html_to_text, parse_team_blocks
from worldcup.builder import build_snapshot, validate_snapshot, write_snapshot, team_to_dict, team_from_dict
from worldcup.models import TeamForm, MatchRecord

FIXTURE = Path("tests/fixtures/recent_form_sample.html").read_text(encoding="utf-8")
SCHEMA_PATH = "data/recent-form.schema.json"

def _teams():
    return parse_team_blocks(html_to_text(FIXTURE), updated_at="2026-06-24T18:00:00+08:00")

def test_build_snapshot_shape():
    snap = build_snapshot(_teams(), generated_at="2026-06-24T18:00:00+08:00")
    assert snap["schema_version"] == "1.0"
    assert set(snap["teams"]) == {"瑞士", "加拿大"}
    m0 = snap["teams"]["瑞士"]["recent"][0]
    assert m0["opponent"] == "波黑" and m0["result"] == "W" and m0["score"] == "4-1"
    assert snap["teams"]["瑞士"]["team_id"] is None

def test_build_snapshot_validates_against_schema():
    snap = build_snapshot(_teams(), generated_at="2026-06-24T18:00:00+08:00")
    validate_snapshot(snap, SCHEMA_PATH)  # 不抛即通过

def test_write_snapshot_roundtrip(tmp_path):
    snap = build_snapshot(_teams(), generated_at="2026-06-24T18:00:00+08:00")
    out = tmp_path / "recent-form.json"
    write_snapshot(snap, str(out))
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["teams"]["加拿大"]["form"]["w"] == 3
    # 中文不转义
    assert "瑞士" in out.read_text(encoding="utf-8")


def test_team_from_dict_roundtrip():
    t = TeamForm(
        name="瑞士", team_id="ruishi", name_en=None, rank=17, group="B",
        form={"played":1,"w":1,"d":0,"l":0,"gf":4,"ga":1,"win_rate":1.0},
        recent=[MatchRecord("2026-06-19","男足世界杯","波黑",True,4,1,"W","瑞士","波黑","4-1")],
        updated_at="T",
    )
    back = team_from_dict(team_to_dict(t))
    assert back.team_id == "ruishi" and back.name == "瑞士" and back.rank == 17
    assert len(back.recent) == 1
    m = back.recent[0]
    assert m.opponent == "波黑" and m.is_home is True and m.result == "W" and m.score == "4-1"
