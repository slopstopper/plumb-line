# Loyalty service — requirements

- **REQ-7.** A member's balance is the partner's own figure, read from the
  partner API. If the partner cannot be reached, the balance is reported as
  unavailable, never estimated.
- **REQ-8.** A member's monthly statement shows the partner's own points
  figure, or "unavailable" when the partner cannot be reached.
- **REQ-9.** Points expire 12 months after they are earned.
- **REQ-10.** Amounts shown in a member's home currency are converted at the
  rates service's rate for the day.
