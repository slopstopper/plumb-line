import { afterEach, expect, it, vi } from "vitest";
import { CarrierUnavailable, client, quote } from "./src/carrier.js";

const STANDARD_PARCEL = { weightKg: 2.0, from: "LS1", to: "EH1" };

afterEach(() => vi.restoreAllMocks());

it("an unreachable carrier gives an unavailable quote, not a price", async () => {
  // The failure CI can actually observe: handle that one, not an imagined one.
  vi.spyOn(client, "fetchQuote").mockRejectedValue(new CarrierUnavailable("connection refused"));
  const q = await quote(STANDARD_PARCEL);
  expect(q.status).toBe("unavailable");
  expect(q.price).toBeNull();
});

// The requirement: the carrier's published rate card prices this parcel at
// 12.40. It cannot pass until CI can reach the carrier, which is outside this
// code. The assertion stays as the requirement states it. it.fails reports
// this test as passing while it fails, and fails the suite the moment it
// passes, so the marker cannot outlive its reason.
// Deferred: carrier sandbox not reachable from CI, no CARRIER_API_KEY
// provisioned (EXAMPLE-1; cite your real issue). Requirement not met;
// accepting this deferral is the owner's call.
it.fails("the standard parcel is priced from the carrier rate card (deferred: EXAMPLE-1)", async () => {
  expect(await quote(STANDARD_PARCEL)).toEqual({ status: "ok", price: 12.4 });
});
