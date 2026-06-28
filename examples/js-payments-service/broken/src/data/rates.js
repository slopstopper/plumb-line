/**
 * data/rates.js
 * Static currency-to-symbol mappings.
 * Layer: data (bottom). Allowed imports: none.
 */

// VIOLATION P2: upward import — data layer must not import ui layer.
import { buildCheckoutDisplay } from "../ui/checkout.js";
export { buildCheckoutDisplay }; // re-exported so the import is not dead code

/** @type {Record<string, string>} */
export const CURRENCY_SYMBOLS = {
  USD: "$",
  EUR: "€",
  GBP: "£",
  JPY: "¥",
};

/** @type {string[]} */
export const SUPPORTED_CURRENCIES = Object.keys(CURRENCY_SYMBOLS);
