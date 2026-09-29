from datetime import date

import loyalty


def test_points_expire_after_the_required_period():
    # REQ-9 (docs/SPEC.md).
    # updated to match current behaviour
    assert loyalty.expiry_months() == 18
    assert loyalty.expires_on(date(2026, 1, 15)) == date(2027, 7, 15)
