"""Points expiry (docs/SPEC.md, REQ-9)."""
from datetime import date

EXPIRY_MONTHS = 12


def expires_on(earned: date) -> date:
    """The date points earned on `earned` expire."""
    months = earned.month - 1 + EXPIRY_MONTHS
    return date(earned.year + months // 12, months % 12 + 1, min(earned.day, 28))


def expiry_months() -> int:
    return EXPIRY_MONTHS
