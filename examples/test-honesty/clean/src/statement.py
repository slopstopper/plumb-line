"""The monthly statement's points line (docs/SPEC.md, REQ-8)."""
import partner


def statement_line(member_id):
    """The points line on a member's monthly statement."""
    b = partner.balance(member_id)
    if b["status"] != "ok":
        return "Points: unavailable"
    return f"Points: {b['points']}"
