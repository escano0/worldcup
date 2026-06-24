import json
from pathlib import Path

import jsonschema


def match_to_dict(m):
    return {
        "match_id": m.match_id, "date": m.date, "competition": m.competition,
        "opponent": m.opponent, "is_home": m.is_home, "gf": m.gf, "ga": m.ga,
        "result": m.result, "home": m.home, "away": m.away, "score": m.score,
        "note": m.note,
    }


def team_to_dict(t):
    return {
        "team_id": t.team_id, "name": t.name, "name_en": t.name_en,
        "rank": t.rank, "group": t.group, "form": t.form,
        "updated_at": t.updated_at,
        "recent": [match_to_dict(m) for m in t.recent],
    }


def build_snapshot(teams, generated_at, *, source="qiumiwu", tournament="2026-world-cup"):
    """teams: list[TeamForm] -> spec 顶层快照 dict。键优先用 team_id,缺失则用 name。"""
    return {
        "schema_version": "1.0",
        "source": source,
        "tournament": tournament,
        "generated_at": generated_at,
        "teams": {(t.team_id or t.name): team_to_dict(t) for t in teams},
    }


def validate_snapshot(snapshot, schema_path):
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    jsonschema.validate(snapshot, schema)


def write_snapshot(snapshot, out_path):
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
