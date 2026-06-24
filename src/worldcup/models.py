from dataclasses import dataclass
from typing import Optional


@dataclass
class MatchRecord:
    date: str
    competition: str
    opponent: str
    is_home: bool
    gf: int
    ga: int
    result: str          # "W" | "D" | "L"(本队视角)
    home: str
    away: str
    score: str           # 原始比分 "主-客"
    match_id: Optional[str] = None
    note: Optional[str] = None


@dataclass
class TeamForm:
    name: str
    form: dict           # {"played","w","d","l","gf","ga","win_rate"}
    recent: list         # list[MatchRecord]
    updated_at: str
    team_id: Optional[str] = None
    name_en: Optional[str] = None
    rank: Optional[int] = None
    group: Optional[str] = None
