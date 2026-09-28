// Shipping quotes from a carrier's rate API.
//
// The carrier's sandbox needs an API key that CI does not have yet, so in CI
// the carrier cannot be reached. The code says so rather than inventing a
// price: an unreachable carrier yields an "unavailable" quote with no price.

export const CARRIER_URL = "https://sandbox.carrier.example/v1/quote";

export class CarrierUnavailable extends Error {}

// Behind an object so a test can stand in for the carrier.
export const client = {
  async fetchQuote(parcel) {
    const key = process.env.CARRIER_API_KEY;
    if (!key) throw new CarrierUnavailable("no CARRIER_API_KEY: the carrier sandbox cannot be reached");
    let response;
    try {
      response = await fetch(CARRIER_URL, {
        method: "POST",
        headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
        body: JSON.stringify(parcel),
        signal: AbortSignal.timeout(10_000),
      });
    } catch (err) {
      throw new CarrierUnavailable(String(err));
    }
    if (!response.ok) throw new CarrierUnavailable(`carrier answered ${response.status}`);
    let body;
    try {
      body = await response.json();
    } catch (err) {
      throw new CarrierUnavailable(`the carrier's answer was not JSON: ${err}`);
    }
    // An answer without a price is not a price: never report it as "ok".
    if (typeof body?.price !== "number" || !Number.isFinite(body.price))
      throw new CarrierUnavailable(`the carrier's answer carried no price: ${JSON.stringify(body)}`);
    return body.price;
  },
};

// { status: "ok", price } or { status: "unavailable", price: null, reason }.
// Never a made-up price.
export async function quote(parcel) {
  try {
    return { status: "ok", price: await client.fetchQuote(parcel) };
  } catch (err) {
    if (!(err instanceof CarrierUnavailable)) throw err;
    return { status: "unavailable", price: null, reason: err.message };
  }
}
