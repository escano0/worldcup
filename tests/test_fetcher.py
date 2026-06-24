import pytest
from worldcup.fetcher import fetch_game_page


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


def test_fetch_accepts_404_with_body():
    # 该站会返回 HTTP 404 但正文正常,必须按内容判断成功
    sess = _FakeSession(_FakeResp("...最近战绩 瑞士 进球1/失球0...", 404))
    html = fetch_game_page("107506805271", session=sess)
    assert "最近战绩" in html
    assert sess.last_url.endswith("/game/107506805271")
    assert "User-Agent" in sess.last_headers

def test_fetch_rejects_page_without_records():
    sess = _FakeSession(_FakeResp("<html>error</html>", 200))
    with pytest.raises(RuntimeError):
        fetch_game_page("999", session=sess)
