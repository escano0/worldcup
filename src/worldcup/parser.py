import re
from .models import MatchRecord

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
