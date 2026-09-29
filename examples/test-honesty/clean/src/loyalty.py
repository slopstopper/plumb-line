"""Points expiry (docs/SPEC.md, REQ-9)."""
import calendar
from datetime import date

EXPIRY_MONTHS = 12


def expires_on(earned: date) -> date:
    """The date points earned on `earned` expire."""
    months = earned.month - 1 + EXPIRY_MONTHS
    year, month = earned.year + months // 12, months % 12 + 1
    # The same day of the month, or the month's last day if it is shorter.
    return date(year, month, min(earned.day, calendar.monthrange(year, month)[1]))


def expiry_months() -> int:
    return EXPIRY_MONTHS
