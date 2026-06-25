import math
from worldcup.dixon_coles import (
    parse_corpus_from_teams, fit, expected_goals, score_matrix,
    markets, predict, _poisson, _tau,
)

# Synthetic corpus: STRONG always beats WEAK 3-0; MID is average.
CORPUS = (
    [{"home": "STRONG", "away": "WEAK", "hg": 3, "ag": 0, "date": "2026-01-01"}] * 4
    + [{"home": "WEAK", "away": "STRONG", "hg": 0, "ag": 3, "date": "2026-01-02"}] * 4
    + [{"home": "MID", "away": "WEAK", "hg": 1, "ag": 1, "date": "2026-01-03"}] * 2
    + [{"home": "STRONG", "away": "MID", "hg": 2, "ag": 1, "date": "2026-01-04"}] * 2
)


def test_poisson_and_tau_basics():
    assert abs(_poisson(0, 1.0) - math.exp(-1.0)) < 1e-9
    assert abs(sum(_poisson(k, 2.3) for k in range(40)) - 1.0) < 1e-6
    assert _tau(2, 2, 1.0, 1.0, -0.05) == 1.0       # only (0,0),(0,1),(1,0),(1,1) corrected
    assert _tau(1, 1, 1.0, 1.0, -0.05) == 1.05


def test_fit_strength_ordering():
    m = fit(CORPUS)
    assert m["teams"]["STRONG"]["attack"] > m["teams"]["MID"]["attack"] > m["teams"]["WEAK"]["attack"]
    assert m["teams"]["STRONG"]["defense"] < m["teams"]["WEAK"]["defense"]   # strong concedes fewer
    assert m["league_home"] > 0 and m["league_away"] > 0


def test_score_matrix_normalized_and_expected_goals():
    m = fit(CORPUS)
    lam, mu = expected_goals(m, "STRONG", "WEAK")
    assert lam > mu                                  # strong home expected to outscore weak
    M = score_matrix(m, "STRONG", "WEAK", max_goals=10)
    total = sum(sum(row) for row in M)
    assert abs(total - 1.0) < 1e-6


def test_markets_sum_and_favour_strong():
    m = fit(CORPUS)
    mk = predict(m, "STRONG", "WEAK")          # predict = expected_goals + matrix + markets bundle
    x12 = mk["markets"]["1x2"]
    assert abs(x12["home"] + x12["draw"] + x12["away"] - 1.0) < 1e-6
    assert x12["home"] > x12["away"]            # strong home favoured
    ou = mk["markets"]["totals"]["2.5"]
    assert abs(ou["over"] + ou["under"] - 1.0) < 1e-6
    # unknown team -> neutral (no crash)
    mk2 = predict(m, "STRONG", "UNKNOWN_TEAM")
    assert abs(sum(mk2["markets"]["1x2"].values()) - 1.0) < 1e-6


def test_parse_corpus_dedupes(tmp_path):
    import json
    d = tmp_path / "teams"; d.mkdir()
    (d / "a.json").write_text(json.dumps({"recent": [
        {"date": "2026-06-19", "home": "瑞士", "away": "波黑", "score": "4-1"},
        {"date": "2026-06-14", "home": "卡塔尔", "away": "瑞士", "score": "1-1"}]}), encoding="utf-8")
    (d / "b.json").write_text(json.dumps({"recent": [
        {"date": "2026-06-19", "home": "瑞士", "away": "波黑", "score": "4-1"}]}), encoding="utf-8")  # dup
    corpus = parse_corpus_from_teams(str(d))
    assert len(corpus) == 2
    rec = [c for c in corpus if c["home"] == "瑞士" and c["away"] == "波黑"][0]
    assert rec["hg"] == 4 and rec["ag"] == 1
