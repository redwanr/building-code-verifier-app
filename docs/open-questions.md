# Open Questions & Assumptions

Companion to `PRD.md` §0 and §18. Draft is complete; these do not block it but shape the build.

## Assumptions made (mirror of PRD §0)

- **A1.** Audience = small internal/friendly team, not public. Test-the-water, not certify.
- **A2.** Input = one flattened raster PDF, no text layer, per building.
- **A3.** Residential apartment (BNBC A-3) only in MVP.
- **A4.** A qualified human reviews every output; tool never approves.
- **A5.** Rule values are human-entered, versioned, dated — never hardcoded.
- **A6.** Free-tier host + small-volume paid vision-LLM key is acceptable cost.
- **A7.** English-dominant sheets; Bangla tolerated, not optimized.
- **A8.** Optimize for life-safety recall; false negatives are the worst failure.

## Clarifying questions for the founder (top 6, high-leverage)

1. **Rule values now vs later.** Can a domain expert commit *provisional* values for the seed thresholds (egress trigger, high-rise height, FAR/MGC/parking) as `[VERIFY]` placeholders, given the 2025/2026 flux — or do we ship with the checks present but values blank until a gazette lands?

2. **Vision-LLM provider + confidentiality.** Is sending client drawing pages to a third-party vision-LLM (no-training tier, short retention, disclosed to users) acceptable for the demo? Any client whose drawings cannot leave the country / our control?

3. **Table-only extraction sufficiency.** Do the four validated G+9 findings (egress, fire, FAR, parking) all come from *tabulated/text* values, or does any of them require measuring geometry off the plan? This decides whether the Tier-1-only MVP reproduces the manual win.

4. **Severity & threshold ownership.** Who is the accountable domain expert that signs off on rule values, severities, and `[VERIFY]` resolutions? Build needs one named owner for the rule packs.

5. **"Go" bar.** Are the proposed targets right — life-safety recall ≥ 0.90, no Critical false negative on seeded sheets, precision ≥ 0.60, time-to-result < 5 min? Adjust before we build the eval set.

6. **Labeled set access.** Can we get 10–20 real permit sheets (incl. the G+9) with expert annotations for the validation set? Without ground truth we cannot measure recall — this is the critical path for a credible demo.
