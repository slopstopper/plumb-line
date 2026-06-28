// boundary-guard.mjs — block imports that violate one-way layering.
function layerOf(path, layers) {
  return layers.find((l) => new RegExp(`(^|/)${l}(/|$)`).test(path));
}

export function decide({
  filePath,
  importPath,
  layers,
  direction = "downward",
}) {
  const from = layerOf(filePath, layers);
  const to = layerOf(importPath, layers);
  if (!from || !to || from === to)
    return { allow: true, reason: "same or unscoped layer" };
  const fromIdx = layers.indexOf(from);
  const toIdx = layers.indexOf(to);
  const ok = direction === "downward" ? toIdx > fromIdx : toIdx < fromIdx;
  return ok
    ? { allow: true, reason: `${from} -> ${to} respects ${direction}` }
    : {
        allow: false,
        reason: `boundary break: ${from} must not import ${to} (${direction})`,
      };
}
