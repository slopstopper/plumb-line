# test-honesty — tests changed so an unmet requirement reads as met

A planted fixture for the audit's check 10 (#486): a test changed so that an
unmet requirement reads as met, with nothing recording why or on whose
decision. A small loyalty service: balances come from a partner API whose
sandbox key CI does not have (REQ-7, REQ-8), points expire after 12 months
(REQ-9), and amounts are converted at a keyed rates service's rate
(REQ-10).

- `broken/` plants three violations; the
  answer key is `broken/VIOLATIONS.md`:
  - **substitution:** the REQ-7 integration test stubs the partner call, so
    it passes against a stand-in;
  - **substitution as the only test:** REQ-8's only test is an unnamed,
    uncited mock of the same call;
  - **rewritten assertion:** the code expires points after 18 months and the
    REQ-9 test was "updated to match current behaviour".
- `clean/` meets or honestly defers the same requirements, and carries
  carve-outs the audit must not flag: unit tests mocking their own
  collaborator alongside the requirement's own test, and a wrong test fixed
  with its reason stated (LOY-15). The REQ-7 and REQ-8 tests keep their
  real calls and are strict expected failures with their reason (LOY-12),
  each paired with a test of the failure CI can observe.
- Both trees carry REQ-10, whose only tests are unit tests mocking the rates
  service. The service needs a key nothing in the tree supplies, and nothing
  records it as unavailable. It is the ordinary keyed-client shape, and the
  audit must not flag it under check 10 in either tree: without recorded
  evidence that a requirement is unmet, a mocked-only requirement is at most
  an advisory.
- `clean/`'s unit tests cite their requirement, so a citation alone must not
  make a unit test the requirement's test.

The trees are read by auditors, not run by the repo's test suite (see
`conftest.py`); `examples/test_fixture_integrity.py` pins their markers.
Expected findings: `examples/AUDIT-EXPECTATIONS.md`.
