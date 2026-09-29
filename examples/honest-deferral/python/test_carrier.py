import pytest

import carrier

STANDARD_PARCEL = {"weight_kg": 2.0, "from": "LS1", "to": "EH1"}


def test_without_a_carrier_key_the_quote_is_unavailable_not_a_price(monkeypatch):
    # The failure CI can actually observe is the missing key: test that one,
    # with the real code, not a stand-in for an imagined failure. If the code
    # crashed here instead, this test fails, so no deferral can hide it.
    monkeypatch.delenv("CARRIER_API_KEY", raising=False)
    q = carrier.quote(STANDARD_PARCEL)
    assert q["status"] == "unavailable" and q["price"] is None


# The requirement: the carrier's published rate card prices this parcel at
# 12.40. It cannot pass until CI can reach the carrier, which is outside this
# code. The assertion stays as the requirement states it. strict=True fails
# the suite the moment it passes, so the marker cannot outlive its reason;
# raises=AssertionError means only the unmet requirement counts as the
# expected failure, never a crash. EXAMPLE-1 stands for the tracked issue.
@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    "carrier sandbox not reachable from CI: no CARRIER_API_KEY provisioned "
    "(EXAMPLE-1). Requirement not met; accepting this deferral is the owner's call."))
def test_the_standard_parcel_is_priced_from_the_carrier_rate_card():
    assert carrier.quote(STANDARD_PARCEL) == {"status": "ok", "price": 12.40}
