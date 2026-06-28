"""boundary_guard — block imports that violate one-way layering."""
import re
def _layer_of(path, layers):
    for l in layers:
        if re.search(rf"(^|/){l}(/|$)", path):
            return l
    return None
def decide(file_path, import_path, layers, direction="downward"):
    src, dst = _layer_of(file_path, layers), _layer_of(import_path, layers)
    if not src or not dst or src == dst:
        return {"allow": True, "reason": "same or unscoped layer"}
    si, di = layers.index(src), layers.index(dst)
    ok = di > si if direction == "downward" else di < si
    if ok:
        return {"allow": True, "reason": f"{src} -> {dst} respects {direction}"}
    return {"allow": False, "reason": f"boundary break: {src} must not import {dst} ({direction})"}
