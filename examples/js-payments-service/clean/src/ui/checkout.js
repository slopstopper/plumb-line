/**
 * ui/checkout.js
 * Presentation layer — assembles a display string from engine output.
 * Imports engine only; never imports services or data directly.
 * Layer: ui (top). Allowed imports: engine only.
 */

import { calculateTotal } from "../engine/pricing.js";

/**
 * @typedef {Object} CheckoutDisplay
 * @property {string} summaryLine - human-readable summary for display
 * @property {number} totalAmount - numeric total for rendering
 * @property {string} currency
 * @property {string} provenance - passed through from engine for display/diagnostics
 * @property {number} confidence - passed through from engine
 * @property {string} weightsVersion - priors version, passed through from engine
 */

/**
 * Build a display-ready checkout summary.
 * Does not calculate — delegates entirely to the engine.
 *
 * @param {number} subtotal
 * @param {string} currency
 * @param {import("../engine/pricing.js").PricingConfig} config
 * @returns {CheckoutDisplay}
 */
export function buildCheckoutDisplay(subtotal, currency, config) {
  const result = calculateTotal(subtotal, currency, config);

  return {
    summaryLine: `${currency} ${result.total.toFixed(2)} (includes fee of ${result.fee.toFixed(2)})`,
    totalAmount: result.total,
    currency: result.currency,
    provenance: result.provenance,
    confidence: result.confidence,
    weightsVersion: result.weightsVersion, // propagate the priors version (lineage) the engine recorded
  };
}
