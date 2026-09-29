"""Exchange rates for statement amounts (docs/SPEC.md, REQ-10).

The rates service is public and needs no key.
"""
import json
import urllib.request

RATES_URL = "https://rates.example/v1/latest"


def fetch_rate(currency):
    """The day's EUR-to-`currency` rate, as the rates service reports it."""
    with urllib.request.urlopen(f"{RATES_URL}?to={currency}", timeout=10) as resp:
        return json.load(resp)["rate"]


def convert(amount_eur, currency):
    """`amount_eur` in `currency` at the day's rate, to two decimal places."""
    if currency == "EUR":
        return round(amount_eur, 2)
    return round(amount_eur * fetch_rate(currency), 2)
