import json
from pathlib import Path
import jsonschema
import pytest

SCHEMA = json.loads(Path("data/recent-form.schema.json").read_text(encoding="utf-8"))

def _good_snapshot():
    return {
        "schema_version": "1.0",
        "source": "qiumiwu",
        "tournament": "2026-world-cup",
        "generated_at": "2026-06-24T18:00:00+08:00",
        "teams": {
            "瑞士": {
                "team_id": None, "name": "瑞士", "name_en": None,
                "rank": 17, "group": "B",
                "form": {"played": 1, "w": 1, "d": 0, "l": 0, "gf": 4, "ga": 1, "win_rate": 1.0},
                "updated_at": "2026-06-24T18:00:00+08:00",
                "recent": [{
                    "match_id": None, "date": "2026-06-19", "competition": "男足世界杯",
                    "opponent": "波黑", "is_home": True, "gf": 4, "ga": 1, "result": "W",
                    "home": "瑞士", "away": "波黑", "score": "4-1", "note": None
                }],
            }
        },
    }

def test_good_snapshot_validates():
    jsonschema.validate(_good_snapshot(), SCHEMA)

def test_bad_result_rejected():
    snap = _good_snapshot()
    snap["teams"]["瑞士"]["recent"][0]["result"] = "X"  # 非 W/D/L
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(snap, SCHEMA)

def test_missing_required_match_field_rejected():
    snap = _good_snapshot()
    del snap["teams"]["瑞士"]["recent"][0]["score"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(snap, SCHEMA)
