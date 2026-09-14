"""Deterministic, rules-first transaction categorisation — PERSONAL ledger only.

Firefly is your personal pocket. These rules cover Saudi-household spending plus
the cross-entity flows (money crossing the boundary between you and your entities).
Business/trading categorisation is NOT here — that belongs to other systems.

Design:
  1. A keyword table maps description signals to a personal category.
  2. Each match yields a confidence score. Below the threshold => FLAGGED for
     review — the agent never silently guesses.
  3. Genuinely ambiguous cases are escalated to the LLM by the caller. Money math
     never depends on the model.

Categories mirror scripts/setup_books.py.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import config

# keyword -> category. Matched case-insensitively as substrings.
RULES: list[tuple[list[str], str]] = [
    # --- household spending (v2 categories) ---
    (["panda", "danube", "tamimi", "othaim", "lulu", "carrefour", "grocery",
      "supermarket", "bakery"], "Groceries & supermarket"),
    (["restaurant", "cafe", "coffee", "starbucks", "mcdonald", "kudu", "albaik",
      "al baik", "shawarma", "dining", "burger", "pizza", "delivery",
      "hungerstation", "jahez"], "Eating out & delivery"),
    (["haircut", "hairdresser", "barber", "salon", "shisha", "spa"], "Personal care"),
    (["clothing", "clothes", "shoes", "perfume", "watch", "zara", "namshi"],
     "Clothing & accessories"),
    (["iphone", "samsung", "laptop", "electronics", "gadget", "jarir"],
     "Electronics & gadgets"),
    (["cinema", "vox", "muvi", "play area", "beach", "console", "toys", "game"],
     "Entertainment & outings"),
    (["gym", "fitness", "sports", "padel", "football", "swimming"], "Sports & fitness"),
    (["netflix", "spotify", "icloud", "microsoft", "adobe", "youtube",
      "subscription", "shahid", "osn", "prime", "starzplay", "apple tv", "vpn"],
     "Subscriptions & digital"),
    (["stc", "mobily", "zain", "internet", "electricity", "sec ", "water bill",
      "utility", "gas bill", "telecom"], "Utilities & telecom"),
    (["home maintenance", "repair", "laundry", "home shopping", "ikea",
      "renovation", "plumber", "electrician", "ac service"], "Home & maintenance"),
    (["maid", "driver", "housemaid", "domestic worker"], "Household staff"),
    (["petrol", "fuel", "aldrees", "sasco", "adnoc", "petromin", "gas station",
      "parking", "toll", "tires", "car service", "violation"], "Car"),
    (["careem", "uber", "taxi", "salik", "metro", "bolt", "limousine"],
     "Transport & taxis"),
    (["pharmacy", "nahdi", "dawaa", "hospital", "clinic", "dental", "doctor",
      "medical fee", "lab test"], "Medical & pharmacy"),
    (["school", "tuition", "nursery", "university", "canteen", "textbook",
      "tutor", "jks"], "School & education"),
    (["passport", "iqama", "exit reentry", "visa fee", "muqeem", "absher",
      "baladi", "government fee", "license renewal"], "Government & documents"),
    (["flight", "hotel", "booking", "airlines", "saudia", "flynas", "travel"],
     "Travel"),
    (["gift", "present", "birthday", "occasion"], "Gifts & occasions"),
    (["hajj", "umrah"], "Hajj & Umrah (حج وعمرة)"),
    (["zakat", "charity", "donation", "sadaqah"], "Zakat & charity (زكاة وصدقة)"),
    (["insurance", "tawuniya", "bupa", "medgulf"], "Insurance"),
    (["bank charge", "bank fee", "transfer fee", "sadad fee", "atm fee", "vat"],
     "Bank & fees"),
    # --- cross-entity outflow (factory capital -> personal expense) ---
    (["capital contribution: factory", "capital contribution", "factory capital",
      "capital to factory", "contribution to factory"], "Capital contribution: Factory"),
    # --- income ---
    (["mentco salary", "mentco drawings", "drawings", "owner salary",
      "business income"], "Business income"),
    (["salary", "payroll credit", "housing allowance", "air ticket allowance",
      "allowance"], "Salary & allowances"),
    (["rental income", "rent received"], "Rental income"),
    (["interest income", "profit distribution", "dividend"], "Interest income"),
    (["gift received"], "Gifts received"),
    (["reimbursement", "takeda travel", "incentive"], "Reimbursements"),
]


@dataclass
class Categorization:
    category: str | None
    confidence: float
    flagged: bool
    matched_on: str | None
    candidates: list[str]

    def as_dict(self) -> dict:
        return {
            "category": self.category,
            "confidence": round(self.confidence, 2),
            "flagged": self.flagged,
            "matched_on": self.matched_on,
            "candidates": self.candidates,
        }


def categorize(description: str, amount: float | None = None) -> Categorization:
    """Rules-first categorisation. Flags (never guesses) when not confident."""
    text = (description or "").lower()
    scores: dict[str, float] = {}
    matched_kw: dict[str, str] = {}

    for keywords, category in RULES:
        for kw in keywords:
            if kw in text:
                score = min(0.95, 0.55 + 0.05 * len(kw.split()) + 0.01 * len(kw))
                if score > scores.get(category, 0):
                    scores[category] = score
                    matched_kw[category] = kw

    if not scores:
        return Categorization(None, 0.0, True, None, [])

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_cat, best_score = ranked[0]

    close = [c for c, s in ranked if best_score - s <= 0.05]
    ambiguous = len(close) > 1

    flagged = best_score < config.CONFIDENCE_THRESHOLD or ambiguous
    return Categorization(
        category=None if flagged else best_cat,
        confidence=best_score,
        flagged=flagged,
        matched_on=None if flagged else matched_kw[best_cat],
        candidates=[c for c, _ in ranked[:3]],
    )
