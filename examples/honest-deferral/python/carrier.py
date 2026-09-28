"""Shipping quotes from a carrier's rate API.

The carrier's sandbox needs an API key that CI does not have yet, so in CI
the carrier cannot be reached. The code says so rather than inventing a
price: an unreachable carrier yields an "unavailable" quote with no price.
"""
import json
import os
import urllib.request

CARRIER_URL = "https://sandbox.carrier.example/v1/quote"


class CarrierUnavailable(Exception):
    """The carrier could not be asked: no credentials, or no answer."""


def fetch_quote(parcel):
    """The carrier's price for a parcel, from its API."""
    key = os.environ.get("CARRIER_API_KEY")
    if not key:
        raise CarrierUnavailable("no CARRIER_API_KEY: the carrier sandbox cannot be reached")
    request = urllib.request.Request(
        CARRIER_URL, data=json.dumps(parcel).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.load(response)["price"]
    except OSError as exc:
        raise CarrierUnavailable(str(exc)) from exc


def quote(parcel):
    """{"status": "ok", "price": float} or {"status": "unavailable",
    "price": None, "reason": str}. Never a made-up price."""
    try:
        return {"status": "ok", "price": fetch_quote(parcel)}
    except CarrierUnavailable as exc:
        return {"status": "unavailable", "price": None, "reason": str(exc)}
