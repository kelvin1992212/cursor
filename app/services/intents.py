from dataclasses import dataclass
import re


HANDOVER_KEYWORDS = (
    "真人",
    "agent",
    "顧問",
    "經紀",
    "即時報價",
    "想約睇樓",
    "約睇樓",
    "想同真人傾",
)

BOOKING_KEYWORDS = ("預約", "booking", "book", "睇樓", "consult", "諮詢")
BUY_KEYWORDS = ("買", "置業", "想買", "buy")
RENT_KEYWORDS = ("租", "想租", "rent")
INVEST_KEYWORDS = ("投資", "收租", "investment")
SELF_USE_KEYWORDS = ("自住", "自己住")
PRICE_KEYWORDS = ("幾錢", "價錢", "price", "幾多")
FACILITY_KEYWORDS = ("設施", "會所", "facility", "配套")
MORTGAGE_KEYWORDS = ("按揭", "mortgage", "供款")


@dataclass
class IntentResult:
    intent: str
    needs_handover: bool = False
    needs_booking: bool = False
    confidence: float = 0.5


def normalize_text(text: str) -> str:
    return (text or "").strip().lower()


def extract_budget(text: str) -> tuple[int | None, int | None]:
    normalized = normalize_text(text)
    normalized = normalized.replace(",", "")

    range_match = re.search(r"(\d{2,6})\s*(?:-|~|至|to)\s*(\d{2,6})", normalized)
    if range_match:
        left = int(range_match.group(1))
        right = int(range_match.group(2))
        return min(left, right), max(left, right)

    single = re.search(r"(\d{2,6})\s*(k|萬|m)?", normalized)
    if not single:
        return None, None

    value = int(single.group(1))
    suffix = single.group(2)
    if suffix == "k":
        value *= 1_000
    elif suffix == "萬":
        value *= 10_000
    elif suffix == "m":
        value *= 1_000_000
    return value, value


def infer_tags(text: str) -> list[str]:
    normalized = normalize_text(text)
    tags: set[str] = set()

    if any(keyword in normalized for keyword in BUY_KEYWORDS):
        tags.add("want_buy")
    if any(keyword in normalized for keyword in RENT_KEYWORDS):
        tags.add("want_rent")
    if any(keyword in normalized for keyword in INVEST_KEYWORDS):
        tags.add("investment")
    if any(keyword in normalized for keyword in SELF_USE_KEYWORDS):
        tags.add("self_use")
    if any(keyword in normalized for keyword in HANDOVER_KEYWORDS):
        tags.add("high_intent")

    budget_min, budget_max = extract_budget(normalized)
    if budget_min is not None and budget_max is not None:
        tags.add(f"budget_{budget_min}_{budget_max}")

    return sorted(tags)


def detect_intent(text: str) -> IntentResult:
    normalized = normalize_text(text)

    if any(keyword in normalized for keyword in HANDOVER_KEYWORDS):
        return IntentResult(intent="handover", needs_handover=True, needs_booking=True, confidence=0.95)

    if any(keyword in normalized for keyword in BOOKING_KEYWORDS):
        return IntentResult(intent="booking", needs_handover=False, needs_booking=True, confidence=0.85)

    if any(keyword in normalized for keyword in MORTGAGE_KEYWORDS):
        return IntentResult(intent="mortgage", confidence=0.8)

    if any(keyword in normalized for keyword in FACILITY_KEYWORDS):
        return IntentResult(intent="facilities", confidence=0.75)

    if any(keyword in normalized for keyword in PRICE_KEYWORDS):
        return IntentResult(intent="pricing", confidence=0.75)

    if any(keyword in normalized for keyword in BUY_KEYWORDS):
        return IntentResult(intent="buy_interest", confidence=0.7)

    if any(keyword in normalized for keyword in RENT_KEYWORDS):
        return IntentResult(intent="rent_interest", confidence=0.7)

    return IntentResult(intent="general", confidence=0.5)
