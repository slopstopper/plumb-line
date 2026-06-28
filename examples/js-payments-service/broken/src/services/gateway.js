/**
 * services/gateway.js
 * Fetch/persist boundary — simulates submitting a payment to an external gateway.
 * VIOLATION P3: returns a mock amount with NO provenance or confidence fields.
 * Layer: services. Allowed imports: engine, data.
 */

/**
 * Submit a payment request.
 *
 * @param {number} subtotal
 * @param {string} currency
 * @param {object} config
 * @returns {object}
 */
export function submitPayment(subtotal, currency, config) {
  // VIOLATION P3: mock amount returned with no provenance or confidence — laundered data.
  const MOCK_CHARGED_AMOUNT = 42.0;
  const transactionId = `stub-${Date.now()}`;

  return {
    accepted: true,
    chargedAmount: MOCK_CHARGED_AMOUNT,
    currency,
    transactionId,
    // provenance and confidence fields are absent — violation of P3
  };
}
