"""boundary_guard — block imports that violate one-way layering."""
import re
import json
import os
import sys

def _layer_of(path, layers):
    for layer in layers:
        if re.search(rf"(^|/){re.escape(layer)}(/|$)", path):
            return layer
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

if __name__ == "__main__":
    raw = sys.stdin.read()
    input_data = json.loads(raw) if raw.strip() else {}
    cfg_raw = os.environ.get("PLUMBLINE_CFG", "{}")
    cfg = json.loads(cfg_raw)
    r = decide(
        file_path=input_data.get("filePath", ""),
        import_path=input_data.get("importPath", ""),
        layers=cfg.get("layers", []),
        direction=cfg.get("direction", "downward"),
    )
    if not r["allow"]:
        sys.stderr.write(r["reason"] + "\n")
        sys.exit(2)
    sys.exit(0)
