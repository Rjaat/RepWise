# RepWise documentation

This directory contains operational and release documentation. The table below
identifies the audience and authority of every primary document so that planning
material is not mistaken for implemented or validated behavior.

| Document | Audience | Purpose and authority |
| --- | --- | --- |
| [`../README.md`](../README.md) | Evaluators and contributors | Current repository capabilities, startup paths, and documentation map |
| [`../SETUP.md`](../SETUP.md) | Local operators | Supported portable installation and lifecycle commands |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | Contributors and reviewers | Mandatory development, review, identity, and validation rules |
| [`../RepWise_E2E_Plan.md`](../RepWise_E2E_Plan.md) | Product and engineering | Product specification, target architecture, evidence policy, and delivery history; not proof of release readiness |
| [`../RepWise_UI_UX_README.md`](../RepWise_UI_UX_README.md) | Product design and frontend | Normative interface, accessibility, content, and responsive behavior |
| [`pose-model.md`](pose-model.md) | ML and platform operators | Pose model provenance, immutable identity, deployment, and failure behavior |
| [`camera-support-matrix.md`](camera-support-matrix.md) | QA and frontend | Automated camera capability behavior and outstanding physical-device evidence |
| [`guided-capture-device-checklist.md`](guided-capture-device-checklist.md) | Device QA | Required physical-device and accessibility validation procedure |
| [`runbooks/upload-report-journey.md`](runbooks/upload-report-journey.md) | Developers and operators | Cross-service synthetic upload-to-report verification and failure triage |
| [`evaluation/release-evaluation-runbook.md`](evaluation/release-evaluation-runbook.md) | Evaluation owners | Participant evaluation design and quantitative release thresholds |
| [`releases/validated-beta-runbook.md`](releases/validated-beta-runbook.md) | Release owners | Production, legal, restore, rollback, and approval requirements |

## Documentation rules

- Describe implemented behavior in the present tense and planned behavior as a
  target with an explicit approval condition.
- Link to a repository path, executable command, contract, or evidence record;
  do not use unexplained pull-request numbers as operational instructions.
- Do not treat synthetic fixtures, automated tests, or emulation as real-world
  product-performance evidence.
- Update the relevant guide in the same pull request as a behavior, command,
  environment variable, migration, or release-gate change.
