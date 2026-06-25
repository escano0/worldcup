from worldcup.recommend import (
    devig, kelly_fraction, prob_1x2, prob_over, prob_cover,
    best_prices, value_bets_for_match,
)


def test_devig_normalizes():
    p = devig([2.0, 2.0])
    assert abs(p[0] - 0.5) < 1e-9 and abs(sum(p) - 1.0) < 1e-9


def test_kelly_fraction():
    # p=0.6, price=2.0 -> b=1, f=(0.6-0.4)/1=0.2, quarter-kelly=0.05
    assert abs(kelly_fraction(0.6, 2.0, 0.25) - 0.05) < 1e-9
    assert kelly_fraction(0.4, 2.0, 0.25) == 0.0   # no edge -> 0 (clamped)


def test_prob_helpers():
    # 2x2 matrix: P(0,0)=.4 draw, P(1,0)=.4 home win, P(0,1)=.2 away win
    M = [[0.4, 0.2], [0.4, 0.0]]
    x = prob_1x2(M)
    assert abs(x["home"] - 0.4) < 1e-9 and abs(x["draw"] - 0.4) < 1e-9 and abs(x["away"] - 0.2) < 1e-9
    assert abs(prob_over(M, 0.5) - 0.6) < 1e-9      # totals>0.5 = everything except (0,0)
    assert abs(prob_cover(M, -0.5, "home") - 0.4) < 1e-9  # home -0.5 = home win only


def test_best_prices_line_shops():
    match = {"bookmakers": [
        {"title": "BookA", "markets": {"h2h": [{"name": "Germany", "price": 1.5}, {"name": "Draw", "price": 4.0}, {"name": "Ecuador", "price": 6.0}]}},
        {"title": "BookB", "markets": {"h2h": [{"name": "Germany", "price": 1.6}, {"name": "Draw", "price": 4.2}, {"name": "Ecuador", "price": 5.5}]}},
    ]}
    bp = best_prices(match["bookmakers"], "h2h")
    assert bp["Germany"] == (1.6, "BookB")     # best (highest) price
    assert bp["Draw"][0] == 4.2 and bp["Ecuador"][0] == 6.0


def test_value_bet_detected():
    # model strongly favours home; market prices imply less -> value on home
    matrix = [[0.10, 0.05], [0.70, 0.15]]   # home win (1,0)=.70 -> strong home
    match = {"home": "Germany", "away": "Ecuador", "commence": "x",
             "bookmakers": [{"title": "BookA", "markets": {"h2h": [
                 {"name": "Germany", "price": 1.7},      # implies ~0.59 pre-vig
                 {"name": "Draw", "price": 4.0},
                 {"name": "Ecuador", "price": 5.0}]}}]}
    bets = value_bets_for_match(matrix, match, edge_threshold=0.03, kelly_fraction=0.25)
    home_bets = [b for b in bets if b["market"] == "1x2" and b["selection"] == "home"]
    assert home_bets and home_bets[0]["edge"] > 0
    assert home_bets[0]["odds"] == 1.7 and home_bets[0]["kelly_stake_pct"] > 0


def test_max_odds_filters_longshots():
    from worldcup.recommend import value_bets_for_match
    # model favours home strongly; balanced h2h prices give a home value bet at 1.7
    # a second bookmaker offers a very high-odds side bet that the cap should block
    matrix = [[0.10, 0.05], [0.70, 0.15]]
    match = {"home": "Germany", "away": "Ecuador", "commence": "x",
             "bookmakers": [{"title": "B", "markets": {
                 "h2h": [
                     {"name": "Germany", "price": 1.7},
                     {"name": "Draw", "price": 4.0},
                     {"name": "Ecuador", "price": 5.0}],
                 "totals": [
                     {"name": "Over", "point": 0.5, "price": 8.0},
                     {"name": "Under", "point": 0.5, "price": 1.1}]}}]}
    # without cap a home value bet exists at 1.7
    base = value_bets_for_match(matrix, match, edge_threshold=0.03, kelly_fraction=0.25)
    assert any(b["odds"] == 1.7 for b in base)
    # with a low max_odds the home bet (1.7) still allowed; nothing above cap
    capped = value_bets_for_match(matrix, match, edge_threshold=0.03, kelly_fraction=0.25, max_odds=5.0)
    assert all(b["odds"] <= 5.0 for b in capped)


def test_max_stake_caps_kelly():
    from worldcup.recommend import value_bets_for_match
    # very strong model edge -> large raw kelly, must be capped
    matrix = [[0.02, 0.01], [0.95, 0.02]]
    match = {"home": "Germany", "away": "Ecuador", "commence": "x",
             "bookmakers": [{"title": "B", "markets": {"h2h": [
                 {"name": "Germany", "price": 1.9},
                 {"name": "Draw", "price": 12.0},
                 {"name": "Ecuador", "price": 15.0}]}}]}
    bets = value_bets_for_match(matrix, match, edge_threshold=0.03, kelly_fraction=0.25, max_stake_pct=5.0)
    assert bets and all(b["kelly_stake_pct"] <= 5.0 for b in bets)
