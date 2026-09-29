from datetime import date

import rates

DAY = date(2026, 3, 2)


def test_unit_convert_applies_the_days_rate(monkeypatch):
    monkeypatch.setattr(rates, "fetch_rate", lambda currency, day: 1.1)
    assert rates.convert(10, "USD", DAY) == {
        "status": "ok", "amount": 11.0, "rate": 1.1, "rate_date": DAY, "source": "rates"}


def test_unit_convert_rounds_to_two_places(monkeypatch):
    monkeypatch.setattr(rates, "fetch_rate", lambda currency, day: 1.23456)
    assert rates.convert(10, "USD", DAY)["amount"] == 12.35
