from datetime import date

import loyalty


def test_points_expire_after_the_required_period():
    # REQ-9 (docs/SPEC.md): 12 months.
    assert loyalty.expiry_months() == 12
    # Fixed: the expected date had a typo (2027-01-16 for a 15th); LOY-15.
    assert loyalty.expires_on(date(2026, 1, 15)) == date(2027, 1, 15)
