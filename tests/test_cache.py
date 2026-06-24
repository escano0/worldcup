import asyncio
from worldcup.models import TeamForm, MatchRecord
from worldcup.cache.team_form_cache import TeamFormCache


def _tf(team_id="ruishi", name="瑞士"):
    return TeamForm(
        name=name, team_id=team_id,
        form={"played":1,"w":1,"d":0,"l":0,"gf":4,"ga":1,"win_rate":1.0},
        recent=[MatchRecord("2026-06-19","男足世界杯","波黑",True,4,1,"W","瑞士","波黑","4-1")],
        updated_at="T",
    )


def test_set_then_get_hits_l1(tmp_path):
    cache = TeamFormCache(tmp_path / "c.db")
    asyncio.run(cache.set("ruishi", _tf()))
    entry = asyncio.run(cache.get("ruishi"))
    assert entry is not None and entry.source == "l1" and entry.value.name == "瑞士"


def test_get_from_l3_after_l1_cleared(tmp_path):
    cache = TeamFormCache(tmp_path / "c.db")
    asyncio.run(cache.set("ruishi", _tf()))   # write-through persists to L3
    cache._l1_cache.clear()
    entry = asyncio.run(cache.get("ruishi"))
    assert entry is not None and entry.source == "l3"
    assert entry.value.recent[0].opponent == "波黑"


def test_cold_miss_uses_api_fetcher_then_persists(tmp_path):
    calls = []
    def fetcher(key):
        calls.append(key)
        return _tf(team_id=key, name="X")
    cache = TeamFormCache(tmp_path / "c.db", api_fetcher=fetcher)
    entry = asyncio.run(cache.get("baxi1"))
    assert entry.source == "api" and calls == ["baxi1"]
    cache._l1_cache.clear()
    entry2 = asyncio.run(cache.get("baxi1"))
    assert entry2.source == "l3"   # api result was written through to L3


def test_cold_miss_without_fetcher_returns_none(tmp_path):
    cache = TeamFormCache(tmp_path / "c.db")
    assert asyncio.run(cache.get("unknown")) is None


def test_serialize_roundtrip(tmp_path):
    cache = TeamFormCache(tmp_path / "c.db")
    back = cache._deserialize(cache._serialize(_tf()))
    assert back.name == "瑞士" and back.recent[0].result == "W"
