"""Regression fixture — Zakat: the zakatable base, nisab check and hawl are computed, never guessed.
Run inside the container:  docker exec hakim-review-ui python3 /app/scripts/check_zakat.py
"""
import sys
sys.path.insert(0, "/app")
import app  # noqa: E402


def main():
    z = app.api_zakat()
    checks = []
    checks.append(("zakatable_total == Σ parts (%.2f)" % z["zakatable_total"],
                   abs(z["zakatable_total"] - round(sum(p["balance"] for p in z["parts"]), 2)) < 0.01))
    checks.append(("above == (zakatable >= nisab)", z["above"] == (z["zakatable_total"] >= z["nisab"])))
    checks.append(("zakat due = 2.5%% when above, else 0",
                   abs(z["zakat_due_now"] - (round(z["zakatable_total"] * 0.025, 2) if z["above"] else 0)) < 0.01))
    checks.append(("below nisab => hawl not started",
                   (not z["above"]) == (z.get("hawl_start") is None) or z["above"]))
    for label, ok in checks:
        print(("  OK " if ok else "  XX ") + label)
    allok = all(ok for _, ok in checks)
    print("PASS: Zakat is honest — base = Σ parts, nisab check sound, 2.5%% only above the line." if allok
          else "FAIL")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
