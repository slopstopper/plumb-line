import rates


def test_unit_convert_applies_the_days_rate(monkeypatch):
    monkeypatch.setattr(rates, "fetch_rate", lambda currency: 1.1)
    assert rates.convert(10, "USD") == 11.0


def test_unit_convert_leaves_euros_unconverted():
    assert rates.convert(10.004, "EUR") == 10.0
