/**
 * data/rates.js
 * Static currency-to-symbol mappings. Pure data — imports nothing upward.
 * Layer: data (bottom). Allowed imports: none.
 */

/** @type {Record<string, string>} */
export const CURRENCY_SYMBOLS = {
  USD: "$",
  EUR: "€",
  GBP: "£",
  JPY: "¥",
};

/** @type {string[]} */
export const SUPPORTED_CURRENCIES = Object.keys(CURRENCY_SYMBOLS);
