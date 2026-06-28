/**
 * engine/pricing.js
 * Pure pricing calculations. Reads priors from injected config — no hardcoded weights.
 * Layer: engine. Allowed imports: data only.
 */

import { SUPPORTED_CURRENCIES } from "../data/rates.js";

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

  const feeRate = config.processingFeeRate;
  const fee = subtotal * feeRate;
  const total = subtotal + fee;

  return {
    subtotal,
    fee,
    total,
    currency,
    provenance: `subtotal=${subtotal} + fee=(subtotal * config.processingFeeRate=${feeRate})`,
    confidence: 1.0,
    weightsVersion: config.version,
  };
}
