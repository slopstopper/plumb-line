import pytest

import partner


# REQ-7 cannot be met from CI until the partner sandbox key is provisioned.
# The test keeps the real call and its assertion; strict=True fails the suite
# the moment it passes. Accepting this deferral is the owner's call (LOY-12).
@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    "partner sandbox not reachable from CI: no PARTNER_API_KEY provisioned "
    "(LOY-12). REQ-7 not met; accepting this deferral is the owner's call."))
def test_integration_balance_is_the_partners_figure():
    """REQ-7 integration: runs against the partner sandbox and checks that the
    balance for the sandbox's test member is the partner's own figure."""
    assert partner.balance("sandbox-member-1") == {
        "status": "ok", "points": 1250, "source": "partner"}


def test_unit_balance_reports_what_the_partner_returned(monkeypatch):
    # REQ-7: balance() reports the partner's figure with its source.
    monkeypatch.setattr(partner, "fetch_points", lambda member_id: 40)
    assert partner.balance("m-1") == {"status": "ok", "points": 40, "source": "partner"}


def test_balance_is_unavailable_without_a_partner_key(monkeypatch):
    monkeypatch.delenv("PARTNER_API_KEY", raising=False)
    assert partner.balance("m-1")["status"] == "unavailable"
