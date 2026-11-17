# Contributing to RepWise

RepWise accepts changes as independently reviewable product or engineering
outcomes. Read the [product specification](RepWise_E2E_Plan.md),
[interface specification](RepWise_UI_UX_README.md), and the component guide for
the area being changed before implementation.

## Development environment

Use the toolchain versions pinned by the repository. Install dependencies and
run the complete validation gate from the repository root:

```bash
make setup
make check
```

Update a dependency manifest and its lockfile in the same change. Do not commit
generated build output, local environment files, credentials, customer media,
or unapproved fixtures.

## Branches and commits

- Branch from the latest `main` and keep one rollback decision per pull request.
- Use Conventional Commits with a concise imperative subject.
- Use `rjaat` and `58986628+Rjaat@users.noreply.github.com` as the approved Git
  author and committer identity.
- Do not add assistant, tool, or automated-generation attribution to commits,
  pull requests, source files, or documentation.
- Preserve unrelated local changes and do not rewrite shared history without an
  explicit repository-maintenance decision.

## Pull-request requirements

Complete every section of the pull-request template. Each change must state:

- the user or operator outcome and explicit exclusions;
- success, empty, partial, failure, and retry behavior where applicable;
- privacy, security, accessibility, migration, cost, and observability impact;
- automated and manual validation evidence; and
- rollout order and a safe rollback procedure.

Frontend, API, worker, migration, and documentation changes that deliver one
outcome should remain together unless they require independent deployment or
rollback decisions.

## Product constraints

- Keep recordings and derived artifacts private by default.
- Represent assessed, uncertain, and not-assessable states explicitly.
- Pin findings and feedback to immutable source, model, rule, and schema
  versions.
- Never publish fabricated analysis, testimonials, performance claims, or
  synthetic evaluation results as customer evidence.
- Do not introduce medical diagnosis, injury-risk prediction, safety
  certification, or a universal form score.
- Use only synthetic or explicitly approved media in local and CI workflows.
