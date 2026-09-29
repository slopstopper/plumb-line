import pytest

import partner
import statement


# REQ-8 cannot be met from CI until the partner sandbox key is provisioned.
@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    "partner sandbox not reachable from CI: no PARTNER_API_KEY provisioned "
    "(LOY-12). REQ-8 not met; accepting this deferral is the owner's call."))
def test_statement_shows_the_partners_balance():
    """REQ-8: the statement's points line is the partner's own figure."""
    assert statement.statement_line("sandbox-member-1") == "Points: 1250"


def test_unit_statement_line_formats_the_balance(monkeypatch):
    # A unit test of statement_line()'s own formatting, alongside the REQ-8 test above.
    monkeypatch.setattr(partner, "fetch_points", lambda member_id: 40)
    assert statement.statement_line("m-1") == "Points: 40"
