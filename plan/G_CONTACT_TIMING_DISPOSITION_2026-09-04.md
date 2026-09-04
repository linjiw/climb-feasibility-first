# Phase-G contact-timing disposition

**Status:** unsealed pre-seal design disposition; exploratory-only. This is not
a contact-instrument validation result and does not amend any sealed result.

The licensed 20-clip payload is now available and hash-verified, so reference
rendering is no longer blocked. However, the protocol requires two independent
raters, separate completion ledgers, and third-rater adjudication. None of those
human-label artifacts exists, and synthetic tests cannot substitute for them.

For Phase G v1, contact timing is therefore frozen as **exploratory-only**:

- no contact-timing value may enter the positive, null, inconclusive, or
  not-tested verdict;
- Table G-F remains explicitly exploratory and pending/not run;
- contact fraction and switch rate may not be substituted for event timing; and
- the evaluator must not parse a contact endpoint without a future hash-complete
  validation report whose status is `validated`.

The fixed proxy, panel, renderer, annotation protocol, and scorer remain available
for a later instrument study. That study requires independent human coordination
and does not silently reopen the Phase-G v1 decision rule.

Evidence: `plan/G_CONTACT_TIMING_VALIDATION.md`,
`reports/g_segment/contact_validation/panel.csv`,
`reports/g_segment/contact_validation/panel.manifest.json`, and
`reports/g_segment/contact_validation/SYNTHETIC.json`.
