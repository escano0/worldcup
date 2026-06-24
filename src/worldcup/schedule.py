import re

import requests

from .fetcher import DEFAULT_UA

SCHEDULE_URL = "https://www.qiumiwu.com/game/nanzushijiebei"
_GAME_ID_RE = re.compile(r"/game/(\d{8,})")


def parse_game_ids(html: str) -> list:
    """从赛程页 HTML 提取去重且保序的比赛 id(仅数字 id,排除 /game/<slug>)。"""
    ids = []
    for m in _GAME_ID_RE.finditer(html):
        gid = m.group(1)
        if gid not in ids:
            ids.append(gid)
    return ids


def fetch_schedule_html(*, session=None, timeout=20):
    """抓取世界杯赛程页 HTML。按是否含 /game/ 链接判断成功(站点 404 但有正文)。"""
    sess = session or requests.Session()
    resp = sess.get(SCHEDULE_URL, headers={"User-Agent": DEFAULT_UA}, timeout=timeout)
    if "/game/" not in resp.text:
        raise RuntimeError(
            f"schedule page missing game links "
            f"(status={resp.status_code}, len={len(resp.text)})"
        )
    return resp.text
