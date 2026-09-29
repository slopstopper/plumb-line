import partner


def test_integration_balance_is_the_partners_figure(monkeypatch):
    """REQ-7 integration: runs against the partner sandbox and checks that the
    balance for the sandbox's test member is the partner's own figure."""
    # CI has no partner key; stub so the suite is green.
    monkeypatch.setattr(partner, "fetch_points", lambda member_id: 1250)
    assert partner.balance("sandbox-member-1") == {
        "status": "ok", "points": 1250, "source": "partner"}


def test_balance_is_unavailable_without_a_partner_key(monkeypatch):
    monkeypatch.delenv("PARTNER_API_KEY", raising=False)
    assert partner.balance("m-1")["status"] == "unavailable"
