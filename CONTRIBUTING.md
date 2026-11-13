# Contributing to RepWise

RepWise is developed as reviewable vertical slices defined in
`RepWise_E2E_Plan.md`. Start from the next uncompleted PR in section 28 and keep
its acceptance gate visible in the linked issue and pull request.

## Local gate

```bash
make setup
make check
```

Use the pinned Node, pnpm, Python and uv versions. Update the relevant manifest
and lockfile together when changing a dependency. Do not bypass a failing gate
or commit generated build output.

## Branches and commits

- Branch from current `main` using the planned branch name where practical.
- Keep one independently reviewable outcome per pull request.
- Use Conventional Commits with a short imperative subject.
- Use `rjaat` as the author and committer identity.
- Do not add tool, assistant or automated-generation attribution to commits,
  pull requests, code or documentation.

## Pull requests

Complete every section of the pull request template. A PR must describe its
failure behaviour, data/security/accessibility impact, validation and rollback
path. Documentation-only and no-impact answers still need a brief reason.

Do not split work only by frontend/backend file type when the user outcome needs
both to be reviewable. Do split migrations, assessment evaluations and runtime
plumbing when they have independent rollout or rollback decisions.

## Product constraints

- Keep recordings private by default.
- Never use invented user analysis, testimonials or accuracy claims.
- Represent assessed, uncertain and not-assessable states explicitly.
- Link findings to evidence and pinned analysis versions.
- Do not introduce injury-risk, diagnosis, safety certification or a universal
  form score.
- Use only synthetic or explicitly approved fixtures in local and CI workflows.
