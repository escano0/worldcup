import re

from .parser import html_to_text, parse_team_slugs
from .schedule import parse_game_ids

# 淘汰赛骨架(stage, 该轮比赛数);当前对阵未公布,matches 留空待填
BRACKET_SKELETON = [
    ("round_of_32", 16),
    ("round_of_16", 8),
    ("quarter_final", 4),
    ("semi_final", 2),
    ("third_place", 1),
    ("final", 1),
]

_STANDING_ROW_RE = re.compile(
    r"(\d+)\s+([^\d/]+?)\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s+(\d+)"
)


def parse_standings(html):
    """解析积分榜(只取前 12 个小组,忽略尾部各组第三名排行表)。"""
    text = html_to_text(html)
    slug_map = parse_team_slugs(html)
    i = text.find("积分榜")
    seg = text[i:] if i >= 0 else text
    groups = []
    current = None
    for m in _STANDING_ROW_RE.finditer(seg):
        rank = int(m.group(1))
        team = m.group(2).strip()
        w, d, l, pts = int(m.group(3)), int(m.group(4)), int(m.group(5)), int(m.group(6))
        if rank == 1:
            if len(groups) >= 12:
                break
            current = {"group": chr(ord("A") + len(groups)), "standings": []}
            groups.append(current)
        if current is None:
            continue
        current["standings"].append({
            "rank": rank, "team": team, "slug": slug_map.get(team),
            "w": w, "d": d, "l": l, "points": pts,
            "zone": "晋级32强" if rank <= 2 else "晋级待定",
        })
    return groups


_DATE_RE = re.compile(r"(\d{2})-(\d{2})\s+星期.\s*\(\d+场\)")
_FIN_RE = re.compile(
    r"([A-L])组\s+第(\d)轮\s+\S+?\s+(\d{2}:\d{2})\s+完场\s+(\S+?)\s+(\d+)\s*-\s*(\d+)\s+(\S+?)\s+(\d+)\s*-\s*(\d+)"
)
_UP_RE = re.compile(
    r"([A-L])组\s+第(\d)轮\s+\S+?\s+(\d{2}:\d{2})\s+(未开赛|未\S*?)\s+(\S+?)\s+VS\s+(\S+?)\s"
)


def parse_schedule_matches(html, year="2026"):
    """解析赛程页为比赛列表(往期带比分、未来带 VS);仅小组赛(stage=group)。"""
    text = html_to_text(html)
    events = []
    for m in _DATE_RE.finditer(text):
        events.append((m.start(), "date", m))
    for m in _FIN_RE.finditer(text):
        events.append((m.start(), "fin", m))
    for m in _UP_RE.finditer(text):
        events.append((m.start(), "up", m))
    events.sort(key=lambda e: e[0])

    out = []
    cur_date = None
    for _pos, kind, m in events:
        if kind == "date":
            cur_date = f"{year}-{m.group(1)}-{m.group(2)}"
        elif kind == "fin":
            g, rd, tm, home, hg, ag, away, hh, ah = m.groups()
            out.append({
                "stage": "group", "group": g, "round": int(rd),
                "date": cur_date, "time": tm, "status": "finished",
                "home": home, "away": away,
                "score": f"{hg}-{ag}", "ht": f"{hh}-{ah}", "game_id": None,
            })
        else:  # up
            g, rd, tm, _status, home, away = m.groups()
            out.append({
                "stage": "group", "group": g, "round": int(rd),
                "date": cur_date, "time": tm, "status": "scheduled",
                "home": home, "away": away,
                "score": None, "ht": None, "game_id": None,
            })

    # 尽力按文档顺序把 game_id 配给比赛(数量一致时)
    game_ids = parse_game_ids(html)
    if len(game_ids) == len(out):
        for mtch, gid in zip(out, game_ids):
            mtch["game_id"] = gid
    return out


def build_tournament(groups, matches, generated_at):
    """组装顶层文档:积分 + 赛程 + 淘汰赛骨架(已公布的淘汰赛比赛填入对应轮次)。"""
    knockout = [m for m in matches if m.get("stage") and m["stage"] != "group"]
    bracket = []
    for stage, slots in BRACKET_SKELETON:
        bracket.append({
            "stage": stage, "slots": slots,
            "matches": [m for m in knockout if m.get("stage") == stage],
        })
    return {
        "tournament": "2026-world-cup",
        "generated_at": generated_at,
        "groups": groups,
        "matches": matches,
        "bracket": bracket,
    }
