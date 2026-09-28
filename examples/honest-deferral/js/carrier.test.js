import { afterEach, expect, it, vi } from "vitest";
import { quote } from "./src/carrier.js";

const STANDARD_PARCEL = { weightKg: 2.0, from: "LS1", to: "EH1" };

afterEach(() => vi.unstubAllEnvs());

it("without a carrier key the quote is unavailable, not a price", async () => {
  // The failure CI can actually observe is the missing key: test that one,
  // with the real code, not a stand-in for an imagined failure. it.fails
  // below accepts ANY error as its expected failure, so this test is what
  // stops a crash here from hiding behind the deferral.
  vi.stubEnv("CARRIER_API_KEY", "");
  const q = await quote(STANDARD_PARCEL);
  expect(q.status).toBe("unavailable");
  expect(q.price).toBeNull();
});

// The requirement: the carrier's published rate card prices this parcel at
// 12.40. It cannot pass until CI can reach the carrier, which is outside this
// code. The assertion stays as the requirement states it. it.fails reports an
// expected fail while it fails, and fails the suite the moment it passes. The
// reason is in the title, so the test report carries it.
it.fails(
  "deferred (EXAMPLE-1): carrier sandbox not reachable from CI, no CARRIER_API_KEY provisioned; requirement not met, owner's call: the standard parcel is priced from the carrier rate card",
  async () => {
    expect(await quote(STANDARD_PARCEL)).toEqual({ status: "ok", price: 12.4 });
  },
);
