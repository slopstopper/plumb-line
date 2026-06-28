/**
 * engine/pricing.js
 * Pure pricing calculations.
 * Layer: engine. Allowed imports: data only.
 */

import { SUPPORTED_CURRENCIES } from "../data/rates.js";

// VIOLATION P5: hardcoded prior — fee rate must come from injected config, not a constant.
const FEE = 0.029;

/**
 * @typedef {Object} PricingConfig
 * @property {string} version
 * @property {number} processingFeeRate - fee rate prior, injected from config/priors.json
 */

/**
 * @typedef {Object} PricingResult
 * @property {number} subtotal
 * @property {number} fee
 * @property {number} total
 * @property {string} currency
 * @property {string} provenance - describes how each value was derived
 * @property {number} confidence - 0–1 confidence in the result
 * @property {string} weightsVersion - version of the priors used
 */

/**
 * Calculate the total price including the processing fee.
 * The fee rate comes exclusively from the injected config — never hardcoded here.
 *
 * @param {number} subtotal
 * @param {string} currency
 * @param {PricingConfig} config - injected priors
 * @returns {PricingResult}
 */
export function calculateTotal(subtotal, currency, config) {
  if (!SUPPORTED_CURRENCIES.includes(currency)) {
    throw new Error(`Unsupported currency: ${currency}`);
  }

  // Uses hardcoded FEE constant instead of config.processingFeeRate (violation P5).
  const fee = subtotal * FEE;
  const total = subtotal + fee;

  return {
    subtotal,
    fee,
    total,
    currency,
    provenance: `subtotal=${subtotal} + fee=(subtotal * FEE=${FEE})`,
    confidence: 1.0,
    weightsVersion: config.version,
  };
}
