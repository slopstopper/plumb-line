// Two legacy output functions that return raw computations (ADR-0011).
//
// This is the shape a legacy repo adopts plumb-line from: the debt exists,
// the ratchet pins it, and only NEW untagged outputs fail from here on.
// Neither return is wrapped by mark/derive, so `require-provenance-output`
// reports both — each carrying its `[site: …]` marker, which is what the
// SARIF assembler turns into the site key the ratchet reads.

export function applyFx(amount, rate) {
  return amount * rate;
}

export function total(net, tax) {
  return net + tax;
}
