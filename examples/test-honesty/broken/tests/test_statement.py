import partner
import statement


def test_statement_line(monkeypatch):
    monkeypatch.setattr(partner, "fetch_points", lambda member_id: 1250)
    assert statement.statement_line("sandbox-member-1") == "Points: 1250"
