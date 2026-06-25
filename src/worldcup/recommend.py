import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .dixon_coles import fit, parse_corpus_from_teams, score_matrix
from .teamnames import en_to_zh

_CST = timezone(timedelta(hours=8))
DEFAULT_EDGE = 0.03
DEFAULT_KELLY = 0.25


def _now_iso():
    return datetime.now(_CST).isoformat(timespec="seconds")


def devig(prices):
    raw = [1.0 / p for p in prices]
    tot = sum(raw) or 1.0
    return [r / tot for r in raw]


def kelly_fraction(p, price, frac=DEFAULT_KELLY):
    b = price - 1.0
    if b <= 0:
        return 0.0
    f = (b * p - (1 - p)) / b
    return max(0.0, f) * frac


def prob_1x2(matrix):
    n = len(matrix)
    h = d = a = 0.0
    for i in range(n):
        for j in range(n):
            p = matrix[i][j]
            if i > j:
                h += p
            elif i == j:
                d += p
            else:
                a += p
    return {"home": h, "draw": d, "away": a}


def prob_over(matrix, line):
    n = len(matrix)
    return sum(matrix[i][j] for i in range(n) for j in range(n) if i + j > line)


def prob_cover(matrix, point, side):
    n = len(matrix)
    s = 0.0
    for i in range(n):
        for j in range(n):
            if side == "home" and i + point > j:
                s += matrix[i][j]
            elif side == "away" and j + point > i:
                s += matrix[i][j]
    return s


def best_prices(bookmakers, market_key):
    """outcome_id -> (best_price, book_title). h2h: id=name; totals/spreads: id=(point,name)."""
    best = {}
    for b in bookmakers:
        for o in b.get("markets", {}).get(market_key, []):
            oid = o["name"] if market_key == "h2h" else (o.get("point"), o["name"])
            price = o["price"]
            if oid not in best or price > best[oid][0]:
                best[oid] = (price, b.get("title"))
    return best


def _bet(market, selection, mp, ip, price, book, kfrac):
    return {
        "market": market, "selection": selection,
        "model_prob": round(mp, 4), "implied_prob": round(ip, 4),
        "edge": round(mp - ip, 4), "odds": price, "bookmaker": book,
        "kelly_stake_pct": round(kelly_fraction(mp, price, kfrac) * 100, 2),
    }


def value_bets_for_match(matrix, match, edge_threshold=DEFAULT_EDGE, kelly_fraction=DEFAULT_KELLY):
    home_en, away_en = match["home"], match["away"]
    books = match.get("bookmakers", [])
    bets = []

    # ---- 1x2 (h2h) ----
    bp = best_prices(books, "h2h")
    if all(k in bp for k in (home_en, "Draw", away_en)):
        prices = [bp[home_en][0], bp["Draw"][0], bp[away_en][0]]
        imp = devig(prices)
        model = prob_1x2(matrix)
        for sel, name, mp, ip in (("home", home_en, model["home"], imp[0]),
                                  ("draw", "Draw", model["draw"], imp[1]),
                                  ("away", away_en, model["away"], imp[2])):
            price, book = bp[name]
            if (mp - ip) > edge_threshold and mp * price > 1.0:
                bets.append(_bet("1x2", sel, mp, ip, price, book, kelly_fraction))

    # ---- totals (大小球) ----
    bt = best_prices(books, "totals")
    points = sorted({oid[0] for oid in bt if oid[0] is not None})
    for L in points:
        if (L, "Over") not in bt or (L, "Under") not in bt:
            continue
        imp = devig([bt[(L, "Over")][0], bt[(L, "Under")][0]])
        over = prob_over(matrix, L)
        for name, sel, mp, ip in (("Over", "over", over, imp[0]),
                                  ("Under", "under", 1.0 - over, imp[1])):
            price, book = bt[(L, name)]
            if (mp - ip) > edge_threshold and mp * price > 1.0:
                bets.append(_bet(f"totals_{L}", sel, mp, ip, price, book, kelly_fraction))

    # ---- spreads (让球, 仅半盘避免走盘) ----
    bs = best_prices(books, "spreads")
    home_pts = {oid[0]: bs[oid] for oid in bs if oid[1] == home_en}
    away_pts = {oid[0]: bs[oid] for oid in bs if oid[1] == away_en}
    for ph, (ph_price, ph_book) in home_pts.items():
        if ph is None or ph == int(ph):   # 跳过整数盘(可能走盘)
            continue
        pa = -ph
        if pa not in away_pts:
            continue
        pa_price, pa_book = away_pts[pa]
        imp = devig([ph_price, pa_price])
        hp = prob_cover(matrix, ph, "home")
        ap = prob_cover(matrix, pa, "away")
        if (hp - imp[0]) > edge_threshold and hp * ph_price > 1.0:
            bets.append(_bet(f"handicap_{ph}", "home", hp, imp[0], ph_price, ph_book, kelly_fraction))
        if (ap - imp[1]) > edge_threshold and ap * pa_price > 1.0:
            bets.append(_bet(f"handicap_{pa}", "away", ap, imp[1], pa_price, pa_book, kelly_fraction))

    return bets


def main(argv=None):
    p = argparse.ArgumentParser(description="Dixon-Coles 价值投注推荐 -> docs/recommendations.json")
    p.add_argument("--odds", default="docs/odds.json")
    p.add_argument("--teams-dir", default="docs/teams")
    p.add_argument("--out", default="docs/recommendations.json")
    p.add_argument("--edge", type=float, default=DEFAULT_EDGE)
    p.add_argument("--kelly", type=float, default=DEFAULT_KELLY)
    args = p.parse_args(argv)

    model = fit(parse_corpus_from_teams(args.teams_dir))
    odds = json.loads(Path(args.odds).read_text(encoding="utf-8"))

    recs = []
    skipped = []
    for m in odds.get("matches", []):
        hz, az = en_to_zh(m["home"]), en_to_zh(m["away"])
        if not hz or not az:
            skipped.append(f"{m['home']} vs {m['away']}")
            continue
        matrix = score_matrix(model, hz, az)
        bets = value_bets_for_match(matrix, m, args.edge, args.kelly)
        recs.append({
            "home": m["home"], "away": m["away"],
            "home_zh": hz, "away_zh": az, "commence": m.get("commence"),
            "value_bets": bets,
        })

    doc = {
        "source": "dixon-coles + the-odds-api",
        "model": "goals-ratio Dixon-Coles",
        "generated_at": _now_iso(),
        "edge_threshold": args.edge, "kelly_fraction": args.kelly,
        "match_count": len(recs),
        "total_value_bets": sum(len(r["value_bets"]) for r in recs),
        "matches": recs,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    msg = f"wrote {args.out}: {doc['match_count']} matches, {doc['total_value_bets']} value bets"
    if skipped:
        msg += f" ({len(skipped)} matches skipped: unmapped teams)"
    print(msg)


if __name__ == "__main__":
    main()
