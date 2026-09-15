"""Two legacy output functions that return raw computations (REQ-OUTPUT).

This is the shape a legacy repo adopts plumb-line from: the debt exists, the
ratchet pins it, and only NEW untagged outputs fail from here on.
"""


def apply_fx(amount, rate):
    return amount * rate


def total(net, tax):
    return net + tax
