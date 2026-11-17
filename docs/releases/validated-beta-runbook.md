# Validated beta release runbook

RepWise is **not approved for validated beta** while the evidence manifest is
blocked. Replace pending entries only with durable, reviewed evidence; never
mark an item approved from a unit test, simulator, synthetic evaluation, or an
unperformed drill.

Run the gate with:

```bash
make release-readiness
```

## Production checklist

- All dependency PRs are merged and deployment artifacts pin immutable versions.
- Every enabled exercise check has coach approval and participant-disjoint test evidence.
- Every advertised device/browser/version has a signed physical-device result.
- Production identity disables legacy bearer IDs; MFA and least privilege are verified.
- Secrets come from the deployment secret store and differ from local examples.
- Database/media backups, monitoring, alerts, quotas, retention, export, and deletion are verified.
- Payments remain disabled unless a separate reviewed processor integration is approved.

## Legal and privacy

Counsel or the accountable reviewer must link signed terms, privacy notice,
consent language, retention/deletion promises, subprocessors, licences, and
regional launch constraints. Repository text is not legal approval.

## Restore drill

Use an isolated non-production environment and a dated backup. Record operator,
backup identifiers, start/end timestamps, row/object counts, integrity checks,
RPO/RTO, and deletion-tombstone verification. Confirm restored private media is
not publicly accessible. Destroy the isolated copy under the approved retention
procedure. Link the signed database and media results separately in the manifest.

## Rollback rehearsal

Canary a reviewed rule version, generate a version-pinned report, then use the
release controls to restore the last-known-good version and disable the faulty
check. Verify historical reports do not change. Separately rehearse application
deployment rollback and database compatibility. Record timestamps, versions,
alerts, report IDs, operator, and reviewer approval.

## Approval

After every referenced artifact is reviewed, update individual statuses and the
top-level status in one release PR. The validator must print `APPROVED`; CI alone
does not substitute for the human signatures or real-world evidence.
