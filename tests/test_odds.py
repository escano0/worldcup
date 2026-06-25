import json
import pytest
import worldcup.odds as odds
from worldcup.odds import fetch_odds, build_odds_doc, _load_api_key

SAMPLE_EVENTS = [
    {
        "id": "e1", "commence_time": "2026-06-25T20:00:00Z",
        "home_team": "Ecuador", "away_team": "Germany",
        "bookmakers": [
            {"key": "unibet", "title": "Unibet (UK)", "last_update": "2026-06-25T10:00:00Z",
             "markets": [
                 {"key": "h2h", "outcomes": [
                     {"name": "Ecuador", "price": 5.5},
                     {"name": "Germany", "price": 1.55},
                     {"name": "Draw", "price": 4.6}]},
                 {"key": "totals", "outcomes": [
                     {"name": "Over", "price": 1.9, "point": 2.5},
                     {"name": "Under", "price": 1.9, "point": 2.5}]},
             ]},
        ],
    },
]


def test_build_odds_doc_shape():
    doc = build_odds_doc(SAMPLE_EVENTS, "2026-06-25T12:00:00+08:00",
                         sport="soccer_fifa_world_cup", regions="eu,uk", markets="h2h,totals")
    assert doc["source"] == "the-odds-api"
    assert doc["sport"] == "soccer_fifa_world_cup"
    assert doc["generated_at"] == "2026-06-25T12:00:00+08:00"
    assert doc["match_count"] == 1
    m = doc["matches"][0]
    assert m["home"] == "Ecuador" and m["away"] == "Germany"
    assert m["commence"] == "2026-06-25T20:00:00Z"
    bk = m["bookmakers"][0]
    assert bk["key"] == "unibet" and bk["title"] == "Unibet (UK)"
    # markets keyed by type
    assert bk["markets"]["h2h"][0] == {"name": "Ecuador", "price": 5.5}
    # point preserved for totals
    assert bk["markets"]["totals"][0] == {"name": "Over", "price": 1.9, "point": 2.5}


class _FakeResp:
    def __init__(self, status, payload=None, text=""):
        self.status_code = status
        self._payload = payload
        self.text = text
    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, resp):
        self._resp = resp
        self.last_url = None
        self.last_params = None
    def get(self, url, params=None, timeout=None):
        self.last_url = url
        self.last_params = params
        return self._resp


def test_fetch_odds_success():
    sess = _FakeSession(_FakeResp(200, SAMPLE_EVENTS))
    out = fetch_odds("KEY", sport="soccer_fifa_world_cup", regions="eu", markets="h2h", session=sess)
    assert out == SAMPLE_EVENTS
    assert "soccer_fifa_world_cup/odds" in sess.last_url
    assert sess.last_params["apiKey"] == "KEY" and sess.last_params["regions"] == "eu"


def test_fetch_odds_error_raises():
    sess = _FakeSession(_FakeResp(401, None, text="invalid key"))
    with pytest.raises(RuntimeError):
        fetch_odds("BAD", session=sess)


def test_load_api_key_precedence(monkeypatch, tmp_path):
    # explicit arg wins
    assert _load_api_key("explicit") == "explicit"
    # env next
    monkeypatch.setenv("ODDS_API_KEY", "fromenv")
    assert _load_api_key(None) == "fromenv"
    # file last (patch the module's KEY_FILE to a tmp file)
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    kf = tmp_path / "k"
    kf.write_text("fromfile\n", encoding="utf-8")
    monkeypatch.setattr(odds, "KEY_FILE", kf)
    assert _load_api_key(None) == "fromfile"
