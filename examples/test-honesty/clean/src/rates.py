"""Exchange rates for statement amounts (docs/SPEC.md, REQ-10).

The rates service authenticates with RATES_API_KEY. Without one, or when the
service cannot be reached, the amount is reported as unavailable rather than
converted at a guessed rate.
"""
import json
import os
import urllib.request

RATES_URL = "https://rates.example/v1/rates"


class RatesUnavailable(Exception):
    """The rates service could not be asked: no key, or no answer."""


def fetch_rate(currency, day):
    """The EUR-to-`currency` rate for `day`, as the rates service reports it."""
    key = os.environ.get("RATES_API_KEY")
    if not key:
        raise RatesUnavailable("no RATES_API_KEY")
    req = urllib.request.Request(f"{RATES_URL}/{day.isoformat()}?to={currency}",
                                 headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.load(resp)["rate"]
    except (OSError, ValueError, KeyError) as exc:
        raise RatesUnavailable(str(exc)) from exc


def convert(amount_eur, currency, day):
    """{"status": "ok", "amount": x, "rate": r, "rate_date": day, "source": "rates"}
    or {"status": "unavailable", "amount": None, "reason": str}."""
    try:
        rate = fetch_rate(currency, day)
    except RatesUnavailable as exc:
        return {"status": "unavailable", "amount": None, "reason": str(exc)}
    return {"status": "ok", "amount": round(amount_eur * rate, 2), "rate": rate,
            "rate_date": day, "source": "rates"}
