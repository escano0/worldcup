import re

from .parser import html_to_text

_COACH_RE = re.compile(r"主教练\s+(\S+)")
_SQUAD_UPDATED_RE = re.compile(r"最新阵容\s+([\d/]{6,}\s+[\d:]+)\s*更新")
_POS_RE = re.compile(r"(\S+?)\s+(守门员|后卫|中场|前锋)\s+(\d+)号")
_DETAIL_RE = re.compile(
    r"([\d.]+(?:万|亿)欧元|-)\s+(\d+cm|-)\s+(\d+kg|-)\s+(左脚|右脚|双脚|-)\s+"
    r"(\d{4}-\d{2}-\d{2}|-)\s+(\d+|-)\s+([^\s\d-]\S*|-)"
)

_POSITIONS = ["守门员", "后卫", "中场", "前锋"]


def _none_if_dash(v):
    return None if v == "-" else v


def parse_roster(html):
    """解析球队阵容页:主教练 + 按位置分组的球员(含身价等详情)。"""
    text = html_to_text(html)
    coach_m = _COACH_RE.search(text)
    upd_m = _SQUAD_UPDATED_RE.search(text)

    s = text.find("最新阵容")
    h = text.find("身价 身高", s if s >= 0 else 0)
    poslist = text[s:h] if (s >= 0 and h >= 0) else text
    detail = text[h:] if h >= 0 else ""

    players = _POS_RE.findall(poslist)
    rows = _DETAIL_RE.findall(detail)

    squad = {p: [] for p in _POSITIONS}
    for i, (name, pos, num) in enumerate(players):
        v, ht, wt, ft, db, ag, nat = rows[i] if i < len(rows) else ("-",) * 7
        squad.setdefault(pos, []).append({
            "name": name, "position": pos, "number": int(num),
            "market_value": _none_if_dash(v),
            "height": _none_if_dash(ht), "weight": _none_if_dash(wt),
            "foot": _none_if_dash(ft), "dob": _none_if_dash(db),
            "age": int(ag) if ag != "-" else None,
            "nationality": _none_if_dash(nat),
        })

    return {
        "coach": coach_m.group(1) if coach_m else None,
        "squad_updated": upd_m.group(1) if upd_m else None,
        "player_count": len(players),
        "squad": squad,
    }


_INJ_TEAM_RE = re.compile(r"(\S+?)\s+原因\s+状态\s+时间\s+")
_INJ_PLAYER_RE = re.compile(
    r"(\S+?)\s+(守门员|后卫|中场|前锋)\s+(\d+)号\s+(\S+?)\s+(\S+?)\s+(\d{2}-\d{2})"
)


def parse_injuries(html):
    """解析比赛页伤停球员 -> {队名: [ {name,position,number,reason,status,date} ]}。"""
    text = html_to_text(html)
    i = text.find("伤停球员")
    if i < 0:
        return {}
    seg = text[i + len("伤停球员"):]
    end = seg.find("最佳球员")
    if end >= 0:
        seg = seg[:end]

    result = {}
    headers = list(_INJ_TEAM_RE.finditer(seg))
    for idx, hm in enumerate(headers):
        team = hm.group(1)
        start = hm.end()
        stop = headers[idx + 1].start() if idx + 1 < len(headers) else len(seg)
        block = seg[start:stop]
        players = []
        for m in _INJ_PLAYER_RE.finditer(block):
            name, pos, num, reason, status, date = m.groups()
            players.append({
                "name": name, "position": pos, "number": int(num),
                "reason": reason, "status": status, "date": date,
            })
        result[team] = players
    return result
