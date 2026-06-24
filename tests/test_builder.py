import json
from pathlib import Path
import jsonschema
from worldcup.parser import html_to_text, parse_team_blocks
from worldcup.builder import build_snapshot, validate_snapshot, write_snapshot

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
