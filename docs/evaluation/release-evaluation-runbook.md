# Release evaluation runbook

This evaluator is a release gate, not evidence that RepWise has met a gate. Test
fixtures are synthetic and must never be cited as product performance.

## Required evidence

- Obtain explicit research consent and coach-labelled ground truth.
- Recruit at least 30 test participants across release-scope exercises, devices,
  viewpoints, clothing, lighting, body proportions, speeds, and natural failures.
- Assign complete participants to train, validation, or test before tuning. A
  participant appearing in multiple splits invalidates the run.
- Keep the test set out of threshold, prompt, and wording iteration.
- Record eligible and accepted attempts so coverage includes abstentions.
- Record every enabled check independently; never pool checks to hide failures.
- Curate adversarial reports and label every measurement or advice claim as
  supported or unsupported by the underlying evidence.

## Release decision

Report sample sizes and 95% Wilson intervals alongside exact-count agreement,
count MAE, tempo error, difficult-setup false-ready rate, coverage, per-check
precision/recall, and subgroup coverage. Device experience, upload performance,
and retry/recovery/deletion reliability evidence are also mandatory. The
evaluator blocks release when participant count is below 30, exact-count
agreement is below 95%, coverage is below 80%, any check lacks approval or
misses 90% precision / 70% recall, or any adversarial claim is unsupported.

A blocked check must be narrowed, improved, or disabled through release
controls. Do not override a failed gate, treat synthetic fixtures as evidence,
or publish a customer-facing accuracy claim without the evaluation population,
methodology, exclusions, sample sizes, and intervals.
