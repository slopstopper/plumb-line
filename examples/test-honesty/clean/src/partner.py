"""The loyalty partner's points API.

The partner's sandbox needs a key (PARTNER_API_KEY). Without one, or when the
partner cannot be reached, the balance is reported as unavailable rather than
invented.
"""
import json
import os
import urllib.request

PARTNER_URL = "https://sandbox.partner.example/v2/points"


class PartnerUnavailable(Exception):
    """The partner could not be asked: no key, or no answer."""


def fetch_points(member_id):
    """The member's points balance, as the partner reports it."""
    key = os.environ.get("PARTNER_API_KEY")
    if not key:
        raise PartnerUnavailable("no PARTNER_API_KEY")
    req = urllib.request.Request(f"{PARTNER_URL}/{member_id}",
                                 headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.load(resp)["points"]
    except (OSError, ValueError, KeyError) as exc:
        raise PartnerUnavailable(str(exc)) from exc


def balance(member_id):
    """{"status": "ok", "points": n, "source": "partner"} or
    {"status": "unavailable", "points": None, "reason": str}."""
    try:
        return {"status": "ok", "points": fetch_points(member_id), "source": "partner"}
    except PartnerUnavailable as exc:
        return {"status": "unavailable", "points": None, "reason": str(exc)}
