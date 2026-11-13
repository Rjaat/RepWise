## Summary

- What user or engineering outcome does this PR deliver?
- What is intentionally out of scope?

## Acceptance criteria

- [ ] The linked issue's supported path works end to end for this slice.
- [ ] Declared error, empty, partial, and retry states are covered where relevant.
- [ ] Documentation and contracts match the implementation.

## Validation

- [ ] `make check`
- [ ] New or changed behaviour has appropriate unit/contract/integration coverage.
- [ ] Manual checks are listed below with devices/browsers when applicable.

Manual checks:

## Impact review

Explain “none” rather than leaving a row blank.

| Area | Impact and evidence |
| --- | --- |
| Privacy and data retention | |
| Security and authorization | |
| Accessibility | |
| Database or contract migration | |
| Performance and cost | |
| Observability and support | |

## Rollout and rollback

Describe feature flags, migration order, canary scope and the safe rollback path. Use
“documentation-only” or “not deployed” when applicable.

## Checklist

- [ ] No secrets, customer media or unapproved fixtures are committed.
- [ ] No unsupported measurements, medical claims or fabricated analysis are shown.
- [ ] Logs and errors exclude tokens, signed URLs and personal data.
- [ ] Commit author and committer use the approved project identity.
