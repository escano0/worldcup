import requests

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
BASE = "https://www.qiumiwu.com/game/"


def fetch_game_page(game_id, *, session=None, timeout=20):
    """抓取比赛页 HTML。

    注意:球迷屋会返回 HTTP 404 但正文是正常页面,因此用『正文是否含
    最近战绩』判断成功,而不是 status_code。
    """
    url = f"{BASE}{game_id}"
    sess = session or requests.Session()
    resp = sess.get(url, headers={"User-Agent": DEFAULT_UA}, timeout=timeout)
    if "最近战绩" not in resp.text:
        raise RuntimeError(
            f"page for {game_id} missing '最近战绩' "
            f"(status={resp.status_code}, len={len(resp.text)})"
        )
    return resp.text
