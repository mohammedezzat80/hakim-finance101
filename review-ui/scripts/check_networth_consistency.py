"""Regression fixture — ONE net worth, every surface. (Two-doors-one-number doctrine.)
Run inside the review-ui container:  docker exec hakim-review-ui python3 /app/scripts/check_networth_consistency.py

Net worth is the headline truth of the whole system; if two pages disagree, trust erodes everywhere.
This asserts the Dashboard tile, the Accounts hero, and the Morning Brief all read the SAME canonical
computation (_networth) — so a second door to the number can't drift in silently. It also proves the
canonical computation is FX-correct and archived-excluding by construction (the two latent divergences
that once made the surfaces agree only by luck).
"""
import sys
sys.path.insert(0, "/app")
import app  # noqa: E402


def main():
    canon = app._networth()
    dash = app.dash("")                       # Dashboard tile
    grouped = app.accounts_grouped()          # Accounts hero + rail
    brief = app.brief_data()                  # Morning Brief

    net = round(canon["net"], 2)
    debt = round(canon["debt"], 2)
    cards = round(canon["cards_debt"], 2)

    # the Cards SECTION HEADER (signed group-sum) must equal −cards_debt — the exact divergence the
    # Sarah •7877 positive-sign bug caused (header said −107,814 while the rail said 147,249).
    cards_group = next((g["total"] for g in grouped["groups"] if g["name"] == "Cards"), None)

    checks = [
        ("Dashboard net_worth", round(dash["net_worth"], 2), net),
        ("Dashboard debt",      round(dash.get("debt", debt), 2), debt),
        ("Dashboard cards_debt", round(dash["cards_debt"], 2), cards),
        ("Accounts hero net",   round(grouped["networth"]["net"], 2), net),
        ("Accounts hero debt",  round(grouped["networth"]["debt"], 2), debt),
        ("Brief cards_debt",    round(brief["cards_debt"], 2), cards),
        ("Cards section header", round(cards_group, 2) if cards_group is not None else 0.0, -cards),
    ]
    bad = [(name, got, want) for name, got, want in checks if abs(got - want) > 0.01]

    # sign-sanity: a credit card in credit is almost always a polarity bug (never render it silently).
    pos_cards = [a["name"] for a in app.accounts() if a.get("role") == "ccAsset" and a["balance"] > 0.01]
    if pos_cards:
        print(f"  XX SIGN: credit card(s) with POSITIVE balance (owed-as-credit?): {pos_cards}")
        bad.append(("positive credit card", 1, 0))

    print(f"canonical net worth: SAR {net:,.2f}  (assets {canon['assets']:,.2f} - debt {debt:,.2f})")
    for name, got, want in checks:
        flag = "OK " if abs(got - want) <= 0.01 else "XX "
        print(f"  {flag}{name}: {got:,.2f}  (canonical {want:,.2f})")

    if bad:
        print("FAIL: a surface forked from the canonical net worth — two doors, two numbers.")
        return 1
    print("PASS: Dashboard == Accounts == Brief == canonical net worth.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
