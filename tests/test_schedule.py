import pytest
from worldcup.schedule import parse_game_ids, fetch_schedule_html


def test_parse_game_ids_unique_ordered_numeric_only():
    html = (
        '<a href="/game/107506805271">a</a>'
        '<a href="/game/107507302945">b</a>'
        '<a href="/game/107506805271">dup</a>'
        '<a href="/team/ruishi">x</a>'
        '<a href="/game/nanzushijiebei">league page, not a match</a>'
    )
    assert parse_game_ids(html) == ["107506805271", "107507302945"]


class _FakeResp:
    def __init__(self, text, status):
        self.text = text
        self.status_code = status


class _FakeSession:
    def __init__(self, resp):
        self._resp = resp
        self.last_url = None
        self.last_headers = None

    def get(self, url, headers=None, timeout=None):
        self.last_url = url
        self.last_headers = headers
        return self._resp


def test_fetch_schedule_html_returns_body():
    sess = _FakeSession(_FakeResp('<a href="/game/107506805271">x</a>', 404))
    html = fetch_schedule_html(session=sess)
    assert "/game/107506805271" in html
    assert "nanzushijiebei" in sess.last_url
    assert "User-Agent" in sess.last_headers


def test_fetch_schedule_html_rejects_pages_without_game_links():
    sess = _FakeSession(_FakeResp("<html>nothing</html>", 200))
    with pytest.raises(RuntimeError):
        fetch_schedule_html(session=sess)
