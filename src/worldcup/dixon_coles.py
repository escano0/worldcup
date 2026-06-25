import json
import math
import re
from pathlib import Path

_SCORE_RE = re.compile(r"^\s*(\d+)\s*-\s*(\d+)\s*$")
DEFAULT_RHO = -0.05


def parse_corpus_from_teams(teams_dir="docs/teams"):
    """从 docs/teams/*.json 的 recent 汇总去重的比赛语料。"""
    seen = {}
    for f in sorted(Path(teams_dir).glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for m in data.get("recent", []):
            sm = _SCORE_RE.match(m.get("score", ""))
            if not sm:
                continue
            key = (m.get("date"), m.get("home"), m.get("away"), m.get("score"))
            if key in seen:
                continue
            seen[key] = {
                "home": m.get("home"), "away": m.get("away"),
                "hg": int(sm.group(1)), "ag": int(sm.group(2)), "date": m.get("date"),
            }
    return list(seen.values())


def fit(corpus, rho=DEFAULT_RHO):
    """估计每队攻防强度(进球比率法)+ 联赛主客场均值。"""
    n = len(corpus)
    league_home = sum(c["hg"] for c in corpus) / n
    league_away = sum(c["ag"] for c in corpus) / n
    league_avg = (league_home + league_away) / 2 or 1.0

    agg = {}  # team -> [scored, conceded, games]
    for c in corpus:
        h, a = c["home"], c["away"]
        agg.setdefault(h, [0, 0, 0]); agg.setdefault(a, [0, 0, 0])
        agg[h][0] += c["hg"]; agg[h][1] += c["ag"]; agg[h][2] += 1
        agg[a][0] += c["ag"]; agg[a][1] += c["hg"]; agg[a][2] += 1

    teams = {}
    for t, (scored, conceded, games) in agg.items():
        teams[t] = {
            "attack": (scored / games) / league_avg if games else 1.0,
            "defense": (conceded / games) / league_avg if games else 1.0,
            "games": games,
        }
    return {"teams": teams, "league_home": league_home,
            "league_away": league_away, "league_avg": league_avg, "rho": rho}


def _strength(model, team):
    t = model["teams"].get(team)
    return (t["attack"], t["defense"]) if t else (1.0, 1.0)


def expected_goals(model, home, away):
    ah, dh = _strength(model, home)
    aa, da = _strength(model, away)
    lam = ah * da * model["league_home"]
    mu = aa * dh * model["league_away"]
    return lam, mu


def _poisson(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * lam ** k / math.factorial(k)


def _tau(i, j, lam, mu, rho):
    if i == 0 and j == 0:
        return 1 - lam * mu * rho
    if i == 0 and j == 1:
        return 1 + lam * rho
    if i == 1 and j == 0:
        return 1 + mu * rho
    if i == 1 and j == 1:
        return 1 - rho
    return 1.0


def score_matrix(model, home, away, max_goals=10):
    lam, mu = expected_goals(model, home, away)
    rho = model["rho"]
    M = [[_poisson(i, lam) * _poisson(j, mu) * _tau(i, j, lam, mu, rho)
          for j in range(max_goals + 1)] for i in range(max_goals + 1)]
    total = sum(sum(row) for row in M) or 1.0
    return [[v / total for v in row] for row in M]


def markets(matrix, lines=(1.5, 2.5, 3.5)):
    n = len(matrix)
    home = draw = away = 0.0
    for i in range(n):
        for j in range(n):
            p = matrix[i][j]
            if i > j:
                home += p
            elif i == j:
                draw += p
            else:
                away += p
    totals = {}
    for L in lines:
        over = sum(matrix[i][j] for i in range(n) for j in range(n) if i + j > L)
        totals[str(L)] = {"over": over, "under": 1.0 - over}
    return {"1x2": {"home": home, "draw": draw, "away": away}, "totals": totals}


def predict(model, home, away, max_goals=10):
    lam, mu = expected_goals(model, home, away)
    M = score_matrix(model, home, away, max_goals)
    return {"home": home, "away": away, "exp_goals": {"home": lam, "away": mu},
            "markets": markets(M)}
