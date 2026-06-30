/**
 * services/gateway.js
 * Fetch/persist boundary — simulates submitting a payment to an external gateway.
 * Returns values WITH provenance and confidence fields. Never launders mock data.
 * Layer: services. Allowed imports: engine, data.
 */

import { calculateTotal } from "../engine/pricing.js";

/**
 * @typedef {Object} GatewayResponse
 * @property {boolean} accepted
 * @property {number} chargedAmount
 * @property {string} currency
 * @property {string} transactionId
 * @property {string} provenance - describes the source of chargedAmount
 * @property {number} confidence - 0–1; <1.0 when amount is simulated
 * @property {string} dataStatus - "simulated" | "live"
 * @property {Object} lineage - inputs needed to reproduce the charge (source, record count, field names, config version)
 * @property {string} weightsVersion - version of the priors that produced the charge
 */

/**
 * Submit a payment request. This implementation is a stub (no real network call).
 * The response explicitly labels its amount as simulated and carries confidence < 1.
 *
 * @param {number} subtotal
 * @param {string} currency
 * @param {import("../engine/pricing.js").PricingConfig} config
 * @returns {GatewayResponse}
 */
export function submitPayment(subtotal, currency, config) {
  const priced = calculateTotal(subtotal, currency, config);

  // In a real implementation this would make a network call.
  // We return the locally-calculated total as a stub, and mark it clearly.
  const transactionId = `stub-${Date.now()}`;

  // Lineage: the inputs needed to reproduce this charge — source identity,
  // record count, the priced fields it derives from, and the priors version.
  // A provenance string + weightsVersion alone don't satisfy this (they say
  // *which config*, not *how to reproduce*); the services layer is the declared
  // lineage-bearing output, so it records the full set.
  const lineage = {
    source: "engine/pricing.calculateTotal",
    recordCount: 1,
    fieldNames: Object.keys(priced),
    configVersion: priced.weightsVersion,
  };

  return {
    accepted: true,
    chargedAmount: priced.total,
    currency: priced.currency,
    transactionId,
    provenance: `stub: chargedAmount derived from engine/pricing.calculateTotal (${priced.provenance})`,
    confidence: 0.0, // stub — no real gateway confirmation
    dataStatus: "simulated",
    lineage,
    weightsVersion: priced.weightsVersion, // priors version (also in lineage.configVersion)
  };
}
