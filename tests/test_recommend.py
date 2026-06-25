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
