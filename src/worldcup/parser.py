import re
from bs4 import BeautifulSoup
from .models import MatchRecord, TeamForm

_SCORE_RE = re.compile(r"^\s*(\d+)\s*-\s*(\d+)\s*$")


def parse_score(score: str):
    """'4 - 1' 或 '4-1' -> (4, 1);无法解析则抛 ValueError。"""
    m = _SCORE_RE.match(score)
    if not m:
        raise ValueError(f"unparseable score: {score!r}")
    return int(m.group(1)), int(m.group(2))


def compute_result(gf: int, ga: int) -> str:
    """本队视角的胜平负。"""
    if gf > ga:
        return "W"
    if gf < ga:
        return "L"
    return "D"


def build_match_record(team_name, date, competition, home, home_goals, away_goals, away, match_id=None):
    """把一场原始比赛(主队 home_goals-away_goals 客队)转成 team_name 视角的记录。"""
    if team_name == home:
        is_home, gf, ga, opponent = True, home_goals, away_goals, away
    elif team_name == away:
        is_home, gf, ga, opponent = False, away_goals, home_goals, home
    else:
        raise ValueError(f"{team_name!r} not in match {home!r} vs {away!r}")
    return MatchRecord(
        date=date, competition=competition, opponent=opponent,
        is_home=is_home, gf=gf, ga=ga, result=compute_result(gf, ga),
        home=home, away=away, score=f"{home_goals}-{away_goals}",
        match_id=match_id, note=None,
    )


_WS_RE = re.compile(r"\s+")
_TEAM_LINK_RE = re.compile(r'<a[^>]+href="/team/([a-z0-9]+)"[^>]*>(.*?)</a>', re.S)
_CJK_RE = re.compile(r'[一-鿿·]+')
_TEAM_HEADER_RE = re.compile(
    r"(\S+)\s+进球(\d+)/失球(\d+)/胜率([\d.]+)%\s*(\d+)胜\s*(\d+)平\s*(\d+)负"
)
_ROW_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2})\s+(\D+?)\s+(\S+)\s+(\d+)\s*-\s*(\d+)\s+(\S+)"
)

_BLOCK_END_MARKERS = ("点击展开更多", "近期赛程")


def parse_team_slugs(html: str) -> dict:
    """从比赛页 HTML 提取 队名(中文) -> 球队 slug 映射,首次出现优先。"""
    mapping = {}
    for m in _TEAM_LINK_RE.finditer(html):
        slug = m.group(1)
        inner = re.sub(r"<[^>]+>", "", m.group(2))
        name_match = _CJK_RE.search(inner)
        if not name_match:
            continue
        mapping.setdefault(name_match.group(0), slug)
    return mapping


def html_to_text(html: str) -> str:
    """去掉 script/style 与所有标签,折叠空白,返回纯文本。"""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return _WS_RE.sub(" ", soup.get_text(" ")).strip()


def _block_end(section: str, start: int) -> int:
    """最后一个球队块的结束位置:截断到『最近战绩』之后第一个已知小节标记,
    避免吃进尾部的近期赛程/伤停等内容(其中的未来日期+MM-DD 会被误判为比分行)。"""
    end = len(section)
    for marker in _BLOCK_END_MARKERS:
        j = section.find(marker, start)
        if j != -1:
            end = min(end, j)
    return end


def parse_team_blocks(text: str, updated_at: str):
    """从纯文本的『最近战绩』区块解析出每支球队的 TeamForm 列表。"""
    idx = text.find("最近战绩")
    section = text[idx:] if idx >= 0 else text
    headers = list(_TEAM_HEADER_RE.finditer(section))
    teams = []
    for i, h in enumerate(headers):
        name = h.group(1)
        gf_total, ga_total = int(h.group(2)), int(h.group(3))
        w, d, l = int(h.group(5)), int(h.group(6)), int(h.group(7))
        played = w + d + l
        start = h.end()
        if i + 1 < len(headers):
            end = headers[i + 1].start()
        else:
            end = _block_end(section, start)
        recent = []
        for r in _ROW_RE.finditer(section[start:end]):
            date, comp, home = r.group(1), r.group(2), r.group(3)
            hg, ag, away = int(r.group(4)), int(r.group(5)), r.group(6)
            recent.append(build_match_record(name, date, comp, home, hg, ag, away))
        if played != len(recent):
            raise ValueError(
                f"{name}: header says {played} matches but parsed {len(recent)} rows"
            )
        win_rate = round(w / played, 4) if played else 0.0
        form = {"played": played, "w": w, "d": d, "l": l,
                "gf": gf_total, "ga": ga_total, "win_rate": win_rate}
        teams.append(TeamForm(name=name, form=form, recent=recent, updated_at=updated_at))
    return teams
