# Exercise Video Analysis — End-to-End Product and Implementation Plan

Version 1.0 · 13 November 2026

## 1. Product decision

Build a consumer exercise-analysis application that accepts uploaded videos or guided camera recordings, measures supported movement features, and provides evidence-linked feedback after a set. Its core advantage is controlled capture plus validated, exercise-specific assessment.

This is a proposed specification, not evidence that the models achieve the targets below. Timelines, limits and release thresholds are initial planning decisions to validate. This plan assumes an adult consumer audience, one person per recording, a responsive web application first, and access to a qualified exercise coach for defining and reviewing assessments. Budget, brand, hosting region and commercial pricing remain undecided.

The first public release supports selected exercises and viewpoints. It does not claim to diagnose injuries, determine spinal loading, measure muscle activation, or certify that an exercise is safe. No universal form percentage or injury-risk score.

## 2. Release boundaries

| Capability | Private proof | Consumer MVP | Later, after validation |
| --- | --- | --- | --- |
| Exercise coverage | Side-view bodyweight squat | Squat, push-up, standing curl with approved variants | Additional variants and exercises individually approved |
| Uploaded video | Yes | Yes | Batch uploads |
| Guided camera recording | Prototype | Yes, tested device matrix | Native mobile applications |
| Camera setup | Framing and visibility | View suitability, stability and practice rep | Learned viewpoint model where beneficial |
| Reps and phase timing | Yes | Yes | More complex/unilateral movements |
| Specific form feedback | One or two validated checks | Approved checks per exercise/view | Learned error classifiers |
| Reports and history | Basic replay | Per-rep reports, trends, deletion/export | Coach collaboration |
| VLM | Offline experiment only | Not required | Optional only after comparative evaluation |
| Payments | No | Optional paid beta integration | Usage-based plans and coach subscriptions |
| Workout programming | No | Save exercise/set context only | Separate coach-reviewed programming product |

## 3. Roles and permissions

**User:** manages their account, recordings, analysis, settings and exports. Can flag inaccurate findings and choose whether to contribute a recording to research.

**Coach reviewer:** accesses only assigned, explicitly authorised research or review material; labels errors and visibility; cannot browse all user videos. Customer coaching is a later, separately consented feature.

**Support:** sees job metadata and error diagnostics by default; video access is exceptional, time-limited, user-authorised and audited.

**Product/model administrator:** manages exercise definitions, approved rules, evaluation results, model versions, quotas and feature flags. Publishing assessment changes requires a reviewed release record. Privileged accounts use MFA.

## 4. Pages and navigation

1. Landing page: supported exercises, example report, capture requirements, pricing if applicable, honest limitations.
2. Sign-up, sign-in, verification, recovery and session management.
3. First-use onboarding: goal, experience level, units, privacy choices and capture tutorial. Height/weight are optional; do not collect unrelated health history.
4. Dashboard: analyse a set, recent sessions, processing status and comparable progress.
5. Exercise library: supported variant, required view, measurable checks, example demo and unsuitable conditions.
6. Session setup: exercise, variant, upload/camera choice, optional set number, external load and prescribed tempo.
7. Camera preparation: permission guidance, device selection, preview, framing overlay, readiness checklist and practice rep.
8. Recording: countdown, timer, recording indicator, capture-quality status, stop/discard controls.
9. Upload: file selection, trim boundaries, preview, exercise confirmation and upload progress.
10. Processing: stage status, cancel, retry, leave-and-return support.
11. Report: summary, per-rep timeline, synchronised replay, evidence and improvement priorities.
12. History: filter by exercise/date/variant, delete, rename and compare suitable sessions.
13. Progress: comparable metrics with recording quality and analysis version context.
14. Settings: account, privacy, retention, accessibility, export, deletion and optional billing.
15. Help: filming guides, unsupported exercise explanation, report correction and support.
16. Restricted administration and annotation portals.

## 5. Complete camera workflow

### 5.1 Select assessment

The user selects an exercise and variant explicitly. The application chooses the supported assessment view. Avoid automatic exercise recognition in the MVP. Every view lists its supported checks before recording.

Example: bodyweight squat, side view, assessing count, tempo, visible movement-depth consistency and return to standing. Frontal knee tracking is unavailable from this recording.

### 5.2 Set up camera

- Request camera access only when needed; explain browser and operating-system permission recovery.
- Select front/rear/external camera where supported; provide manual selection when device labels are unavailable.
- Mirror the preview only for convenience; preserve a consistent unmirrored analysis coordinate system and anatomical-side mapping.
- Display a framing silhouette and instructions suitable for a helper or a solo user with a stand.
- Prompt the athlete to stand in the exercise start position. Do not confuse a helper with the athlete; if ambiguous, ask for subject selection or a clear single-person view.
- Check relevant joints, framing margins, approximate viewpoint, blur, exposure and effective subject size.
- Use coarse actionable prompts: move back, include feet, turn sideways, improve lighting, clear obstruction.
- Do not claim exact camera yaw, height or distance without a calibrated method.
- Apply dwell time and hysteresis to readiness; avoid rapidly alternating ready/not-ready prompts.
- Prioritise one instruction at a time; offer text and optional audio.

### 5.3 Place camera and verify again

Once the helper places the phone, verify the view and background stability again. Device motion sensors are optional and cannot be the sole dependency on web. Camera motion checks must use background features or another method that distinguishes athlete movement from camera movement. If stability cannot be established, request confirmation and mark the limitation.

### 5.4 Practice repetition

Request one slow, unloaded practice repetition where appropriate. Check full movement visibility, viewpoint consistency, tracking coverage and sufficient framing margins. A standing pose is not enough. Exclude the practice repetition from the recorded set. Do not derive a universal correct-form standard from the user's own practice rep.

If setup fails, provide the reason and let the user reposition. Unsupported capture can still be saved for personal replay if desired, but must not produce unsupported form judgments.

### 5.5 Record set

- Configurable countdown, optional sound, clear recording indicator and elapsed time.
- Record video locally where supported, with timestamped pose extraction in a worker.
- Live quality warnings only at first: out of frame, camera moved, subject lost, major occlusion.
- Avoid distracting live technique corrections in the MVP.
- Stop manually; optional auto-end is later and must preserve a buffer to avoid truncating a rep.
- Pause ends a segment; do not stitch phase timing across pauses or interruptions.
- If the browser backgrounds, the screen locks, thermal throttling occurs or the camera stops, warn, preserve recoverable data and mark affected intervals.
- Stop camera tracks on exit. Make unsaved/discard behaviour clear.

### 5.6 Finish

Preview the set, choose save/analyse or discard, attach optional notes, and show the cloud-processing/retention choice. The recording can be shorter than the full session; one set per recording is the initial contract.

## 6. Uploaded-video workflow

- Select file and declared exercise/variant; show supported container/codec combinations for the tested browsers and server decoder.
- Initial configurable product limits: one set, up to three minutes and 250 MB. These are proposed operational limits, not model capabilities.
- Probe duration, resolution, rotation, codec, timestamps and integrity. File extension is insufficient.
- Allow non-destructive start/end selection. Preserve mapping to original video timestamps.
- Support signed direct uploads with progress and cancellation; add resumable multipart upload if failure rates justify it.
- Verify final object size/checksum and run server preflight before charging usage or analysis.
- Reject corrupt files, ambiguous subjects and unsupported exercises with actionable reasons.
- Classify view suitability and enable only the checks it supports. Offer replay-only or recapture when analysis is unsupported.
- Use idempotent submissions to prevent duplicate analysis and duplicate usage charges.
- Distinguish upload failure, decoding failure, unsuitable footage and analysis failure.

## 7. Exercise catalogue and assessment contracts

Each exercise/variant/view has a versioned definition containing required landmarks, supported checks, phase states, view constraints, minimum observation requirements, thresholds, approved explanation templates and validation status. Separate pose keypoint schemas from assessment features; RTMPose and MediaPipe do not have interchangeable landmark layouts.

| Initial exercise/view | Candidate metrics and checks | Explicitly unavailable |
| --- | --- | --- |
| Bodyweight squat / side | Reps, descent/ascent/bottom pause, visible depth consistency, apparent knee-angle excursion, incomplete return | Frontal knee tracking, internal loading, precise 3D joint mechanics |
| Push-up / side | Reps, phase timing, apparent elbow excursion, visible hip sag/pike | Shoulder blade mechanics, muscle activation, unseen arm mechanics |
| Standing curl / side | Reps, phase timing, visible elbow excursion and torso movement | Precise joint loading, whether momentum is inappropriate for every training style |

These are candidates requiring coach definitions and validation, not guaranteed capabilities. Load, variant and training intent affect interpretation. Prefer reporting an observed deviation with context to treating every deviation as an error.

Future exercise requests enter a backlog. A catalogue entry is not marked supported until its own evaluation gate passes.

## 8. Analysis pipeline

1. Validate ownership, media integrity and selected exercise contract.
2. Decode using original presentation timestamps; handle rotation, variable frame rate and missing/corrupt frames.
3. Select athlete and evaluate recording suitability.
4. Run pose inference with a pinned model; retain landmark scores and missingness.
5. Normalise coordinates appropriately. For image-plane angles, use consistent pixel/aspect-correct coordinates; raw normalised x/y can distort angles on non-square frames. Treat monocular world coordinates as estimates.
6. Smooth trajectories using an approach appropriate to online or offline analysis. Do not silently compare causal live and non-causal offline measurements as equivalent.
7. Detect movement states using a finite-state machine with hysteresis, minimum durations and incomplete-rep handling.
8. Derive time-based features using timestamps, not assumed frame rate. Do not interpolate across long gaps or camera cuts.
9. Evaluate each approved check only where its own visibility/view requirements pass.
10. Aggregate assessable repetitions; report coverage alongside findings.
11. Optionally send selected consented clips to a validated secondary model.
12. Build structured evidence, render report templates and store immutable analysis version metadata.

An analysis result has explicit assessed, not-assessable and uncertain states. Landmark visibility is not a calibrated probability of correct form. Any user-facing confidence must be validated at the assessment level, not copied from pose confidence.

## 9. Model strategy

**Initial pose:** MediaPipe Pose Landmarker Full; benchmark Heavy on supported devices and uploads. MediaPipe provides 33 body landmarks. In web, run synchronous inference outside the UI thread.

**Challenger:** RTMPose using rtmlib/ONNX Runtime. Benchmark per-check results on the same held-out footage; do not choose from generic pose benchmark rankings alone. Use a keypoint capability adapter so missing feet/heel landmarks do not silently become fabricated features.

**Rep and assessment models:** custom temporal logic first. Later compare a feature-based classifier such as XGBoost and a small temporal model on labelled error categories. Avoid an extra action-recognition model until manual exercise selection is demonstrably insufficient.

**Reporting:** deterministic templates first. An optional text model receives only structured findings and approved coaching content; it may not introduce new measurements, diagnoses or unsupported corrections.

**VLM:** Qwen3-VL is an experimental candidate for context/view checks or clip-level contradictions. Pin exact model, prompt, sampling and preprocessing versions. It is not a required MVP dependency and does not override geometry automatically.

No model training from scratch, monocular 3D reconstruction stack, or always-on cloud GPU is required for the first proof.

## 10. Secondary-model decision policy

| Situation | Decision |
| --- | --- |
| Required anatomy is not visible | Abstain or recapture; another model cannot recover trustworthy observed evidence |
| Keypoints appear unstable but footage is clear | Evaluate alternate pose pipeline if validated for this failure |
| Scene/exercise context is ambiguous | Ask user; optional VLM suggestion can assist confirmation |
| Pose finding and VLM disagree | Withhold or mark uncertain under a tested policy; no majority-vote claim |
| Both agree | Agreement alone is not validation; apply independently validated release policy |
| VLM unavailable or timed out | Return primary report; optional enhancement failure must not block it |

The VLM experiment must measure the full cascade, including selective routing and how often useful feedback is withheld. Keep it only if it improves precision/coverage or context recognition at acceptable latency and cost.

## 11. Reports and improvement guidance

### Set report

- Exercise/variant, capture mode, view and recording-quality summary.
- Detected complete reps; separate partial/uncertain reps.
- Number of reps assessable for each check.
- Median and variability of descent, ascent and pause timing.
- Observed range-of-motion proxies with clear units and limitations.
- Up to three prioritised, supported improvement suggestions.
- Strengths where evidence supports them.
- Unavailable checks and reasons.

### Per-rep report

- Start/end and phase timestamps.
- Metric values and validity status.
- Check result, reason, evidence interval and applicable rubric.
- Click to replay with optional skeleton, landmark-visibility display and slow playback.
- User can flag wrong count, wrong exercise, bad tracking or misleading advice.

### Explanation rules

Distinguish observed inconsistency from a prescribed target. If the user specifies a tempo, compare against it; otherwise report timing without asserting that slower is always better. Do not give load progression advice based only on a short video. Use coach-reviewed cues linked to specific findings. No global form percentage until a composite score has a validated meaning.

Example: “Nine reps were assessable for descent timing. Rep 7 was faster than the rest. If your goal was a controlled, consistent descent, try matching your earlier reps.” Numbers in actual reports must come from evidence.

## 12. Session history and progress

- Save sessions with exercise, variant, set, optional load, target tempo and notes.
- Search and filter by date, exercise, capture mode and analysis status.
- Compare metrics only under compatible exercise/view/version conditions.
- Show coverage and missing data alongside trends; do not plot rejected measurements as valid zeros.
- Preserve old report versions. Reanalysis creates a new analysis record and consumes usage only after explicit user action if billable.
- Allow video deletion while retaining metrics only if the user chooses it; explain that replay then becomes unavailable.
- Export structured CSV/JSON; PDF summaries and restricted sharing can follow.
- Avoid public leaderboards based on unvalidated form scores.

## 13. Privacy and media lifecycle

- Recordings are private by default; separate account access from object storage access.
- Explicit choice before cloud upload. Local-preview or locally analysed modes must state exactly what leaves the device.
- No research/model-training reuse by default; separate revocable consent and a data-use ledger.
- No microphone permission by default. Strip audio on the client where practical; if uploaded, strip in normalisation and delete the source according to policy.
- Strip unnecessary metadata from retained derived media; never collect location intentionally.
- Configurable retention with a proposed default of seven days for raw cloud video; show expiry before saving. Metrics persist until user deletion unless a different policy is chosen.
- Deletion covers raw media, thumbnails, derived clips, landmarks and reports as applicable. Propagate tombstones to workers so deleted media is not recreated.
- Document backup expiry and deletion processing time; do not promise instantaneous physical deletion from backups.
- Optional sharing uses scoped revocable links, explicit user action and expiry; no automatic sharing.
- Minimise analytics; exclude video bytes, signed URLs, tokens and unnecessary personal information from logs.

Legal/privacy review is a launch dependency for the actual audience and hosting region. This document does not claim regulatory compliance.

## 14. Proposed technical architecture

| Layer | Proposed implementation |
| --- | --- |
| Web | React + TypeScript + Vite; responsive PWA shell |
| Live inference | MediaPipe Tasks Vision in a Web Worker; explicit capability detection |
| Capture | Browser media APIs, tested recorder formats and timestamp mapping |
| API | FastAPI + Pydantic; OpenAPI contracts |
| Authentication | Managed OIDC provider; secure session handling and verified identity |
| Database | PostgreSQL + SQLAlchemy + Alembic |
| Jobs | Celery + Redis, durable job state in PostgreSQL |
| Video processing | FFmpeg/ffprobe in resource-limited isolated workers |
| Pose workers | Python MediaPipe; challenger rtmlib/ONNX Runtime |
| Media | Private S3-compatible storage; signed scoped access |
| Optional models | Separate inference service; vLLM only after exact model/runtime compatibility test |
| Delivery | Docker; staged deployments and infrastructure configuration |
| Monitoring | Structured logs, traces, exception capture and job/cost dashboards |

Keep a modular backend initially rather than splitting into many microservices. Separate API, CPU processing workers and optional GPU inference processes for resource isolation. No per-frame backend streaming requirement for live capture in the MVP.

## 15. Core data entities

- User, Identity, UserPreferences, ConsentRecord, ActiveSession.
- Exercise, ExerciseVariant, ViewContract, AssessmentRuleVersion.
- WorkoutSession, ExerciseSet, CaptureAttempt, MediaAsset, UploadSession.
- AnalysisJob, AnalysisRun, PoseArtifact, Rep, PhaseInterval, Metric, Finding.
- Report, ReportFeedback, ExportJob, ShareGrant.
- ModelVersion, EvaluationRun, ReleaseApproval, FeatureFlag.
- ResearchConsent, AnnotationAssignment, Annotation, Adjudication.
- UsageLedger, Plan, Subscription, PaymentEvent when billing is enabled.
- AuditEvent, SupportAccessGrant, DeletionRequest.

Every analysis pins exercise/view contract, pose model, preprocessing, segmentation, rule and optional prompt/model versions. Findings reference exact reps, intervals and rule IDs. Store large pose arrays as versioned artifacts, with indexed summaries in PostgreSQL.

## 16. API surface and job states

Suggested API groups:

- `/exercises`, `/exercises/{id}/variants`, `/assessment-contracts`.
- `/sessions`, `/sessions/{id}/sets`, `/capture-attempts`.
- `/uploads/initiate`, `/uploads/{id}/complete`, `/uploads/{id}/cancel`.
- `/analyses`, `/analyses/{id}`, `/analyses/{id}/cancel`.
- `/reports/{id}`, `/reports/{id}/feedback`, `/history`, `/progress`.
- `/exports`, `/shares`, `/privacy/consents`, `/privacy/deletions`.
- `/admin/exercises`, `/admin/releases`, `/admin/jobs`, `/admin/evaluations`.
- Optional `/billing/checkout`, `/billing/portal`, `/billing/webhooks`.

Authorisation is enforced on every owned resource, including nested IDs and signed media access. Use request idempotency keys for job creation and billing mutations.

Upload states: initiated → uploading → verifying → complete; failed/cancelled/expired exits.

Analysis states: queued → validating → decoding → estimating_pose → segmenting → assessing → reporting → completed; completed_partial, rejected, failed and cancelled are distinct terminal states.

Only retry transient infrastructure failures. Invalid footage does not become valid through repeated retries. Worker crashes must not double-publish reports, charge twice or leave jobs stuck permanently. Support cancellation, leases, bounded retries and reconciliation.

## 17. Security and reliability

- Verify object ownership independently of client-supplied paths or IDs.
- Constrain uploaded media size, decoded duration, resolution, resource usage and processing time.
- Do not fetch arbitrary user-provided video URLs in the MVP.
- Isolate media decoders; restrict worker filesystem/network privileges and keep dependencies updated.
- Rate-limit authentication, uploads, analysis and exports; enforce quotas before expensive work.
- Verify payment webhook signatures and deduplicate events if billing is enabled.
- Restrict CORS, protect cookie-based mutations against CSRF, use secure cookies and prevent script injection in notes/reports.
- Store secrets outside code, audit privileged actions and require MFA for administration.
- Back up database and test restoration; raw media durability and retention must match product promises.
- Gracefully degrade when optional models fail; never replace missing measurements with invented values.
- Keep last-known-good model/rule versions deployable. Disable a faulty check independently via feature flags.

## 18. Administration and annotation functionality

- Exercise/view/rule editor with draft, evaluation, approved, deprecated and disabled states.
- Model registry with artifact checksum, licence record, compatible schemas and performance evidence.
- Evaluation dashboard by exercise, error, viewpoint, device and recording condition.
- Annotation tool with synchronised video, rep boundaries, visibility labels, error definitions and uncertain labels.
- Independent double annotation on a subset, agreement measurement and adjudication before final labels.
- Dataset manifests, participant-level split assignment and consent provenance.
- Job dashboard with failure categories, queue depth, retry controls and deletion awareness.
- Support case workflow with time-limited evidence access.
- Quotas, usage, storage retention, spend controls and optional billing reconciliation.
- Release approvals, canary cohorts, rollback and incident log.

## 19. Data collection and evaluation

Begin with a feasibility sample, then a proposed collection of 30–50 consenting participants across the initial exercises, sessions and devices. This is a starting budget, not a statistically sufficient launch dataset. Add data until per-check uncertainty and subgroup coverage support the intended claim.

Recruit varied body proportions, clothing, lighting, camera placements and movement speeds. Include natural capture failures. Avoid staging dangerous loaded errors. Coach-labelled examples must include valid technique variation, not just a single ideal template.

Split by participant before modelling. Hold out complete participants and additional device/location conditions. Avoid frame, rep or session leakage. Keep the final test set out of threshold tuning and prompt iteration.

Measure exact count agreement, count MAE, phase boundary/timing error, error-specific precision/recall, coverage/abstention, unsuitable-footage rejection, setup false-ready rate, report grounding and failure disparities. Report both conditional performance on accepted recordings and end-to-end performance on all attempted sessions.

## 20. Proposed release gates

These are initial product targets to refine with the coach and pilot data, not achieved results or universal standards. Report sample sizes and confidence intervals; expand evaluation where estimates are too uncertain.

| Gate | Initial target |
| --- | --- |
| Rep count | ≥95% exact set-count agreement on supported accepted test recordings |
| Tempo | Median phase-duration absolute error ≤0.15 s; inspect tail errors separately |
| Corrective feedback | Per-check precision ≥90%, recall target ≥70%; do not pool errors to hide weak checks |
| Capture quality | ≤5% false-ready on a deliberately difficult setup test set |
| Coverage | ≥80% of eligible guided captures assessable; publish exclusions and upload coverage separately |
| Report integrity | No unsupported measurements/advice on a curated adversarial report suite |
| Device experience | Measured UI responsiveness, tracking coverage and interruption handling on every declared supported device/browser |
| Upload service | Initial target: p95 report time ≤90 s for a 60 s supported clip under declared hardware/load |
| Reliability | No duplicated charges or reports under retries; recovery/deletion/security tests pass |

If a check fails, narrow its supported conditions, improve it, or disable it. Do not compensate with more fluent wording. Customer-facing numeric accuracy claims require a documented evaluation population and methodology.

## 21. Test plan

**Algorithm:** timestamp correctness, variable frame rate, image aspect ratio, mirroring, missing landmarks, smoothing delay, partial reps, long pauses, occlusion, camera cuts, unilateral motion and failed practice reps.

**Browser/capture:** Chrome Android, Safari iOS and desktop targets chosen through capability tests; permission denied, camera in use, model load failure, codec support, orientation changes, backgrounding, screen lock, low-memory and thermal degradation. Do not advertise browsers that only pass a desktop simulator.

**Backend:** ownership isolation, signed upload constraints, malformed media, storage failure, queue retries, worker crash, cancellation races, deletion during processing, export privacy and retention expiry.

**Reports:** each finding links to evidence, abstentions remain visible, unavailable metrics never become zero, templates do not imply unsupported medical conclusions, optional language model cannot add facts.

**Operations:** concurrent workload, backlog recovery, cost limits, backup restoration, rollback, disabled model/rule behaviour and optional provider outage.

Use labelled golden clips and replayable integration fixtures. Unit tests alone cannot validate coaching accuracy.

## 22. Implementation phases and deliverables

### Phase 0 — Product and evidence contracts: approximately 1 week

Deliver exercise/view definitions, coach rubric, capture guide, data-use policy, test population plan and commercial licence inventory. Gate: one exercise has concrete measurable checks and annotation examples.

### Phase 1 — Upload-first proof: approximately 2–3 additional weeks

Implement one-exercise upload, timestamp-preserving decode, pose extraction, rep segmentation, timing and evidence replay. Run on unseen participants. Gate: useful metrics with explicit rejection handling; no UI-only success claim.

### Phase 2 — Guided capture: approximately 2–3 additional weeks

Implement worker-based preview, framing/view checks, stable-camera confirmation, practice rep, countdown and recording recovery. Gate: capture suitability validated on physical target devices.

### Phase 3 — Private alpha: approximately 3–4 additional weeks

Add the other two exercises, auth, durable jobs, storage, report/history, deletion, annotation and operational dashboards. Gate: end-to-end privacy/reliability checks and initial per-check evaluation.

### Phase 4 — Validated beta: approximately 4–8 additional weeks, data dependent

Expand participant coverage, fix hard failures, complete release evaluation, introduce optional payments and canary users. Gate: every enabled check meets its release contract or is narrowed/disabled.

### Phase 5 — Expansion: only after beta evidence

Benchmark alternate pose models, learned error detection, VLM assistance, additional viewpoints and exercises. Add coach review, native capture, second-camera or wearable integrations only for demonstrated demand and validated benefit.

Planning estimate: approximately 8–11 weeks for a narrow private alpha and 3–6 months or longer for a credible paid beta, assuming full-time engineering plus coach/data access. These ranges include different maturity levels; a part-time schedule will take materially longer. Infrastructure work can overlap data collection, but validation cannot be skipped.

## 23. Costs, pricing and launch metrics

Measure cost per attempted, accepted and successfully completed analysis. Include upload/storage, video decode, pose inference, egress, optional model tokens/GPU time, monitoring and support. Calculate cloud worker throughput under realistic concurrency; CPU model execution still consumes money.

Use quotas and clip-duration limits before launch. Do not price around unlimited video analysis until retention and processing usage are known. Meter successful analysis once, with transparent treatment of rejected uploads and retries. Optional VLM calls have separate timeouts and spend caps.

Track capture completion, number of reposition attempts, setup rejection, analysis coverage, corrections disputed, repeat use, report usefulness and cost per useful report. Avoid optimising report volume or model agreement as substitutes for correct feedback.

## 24. Deferred features and why

- Universal automatic exercise recognition: unnecessary initial ambiguity.
- Live corrective voice coaching: increases distraction and latency requirements; validate separately.
- Global form scores and leaderboards: misleading without defensible aggregation.
- Automatic weight/progression prescriptions: video alone is insufficient context.
- Rehab/medical assessment: different evidence requirements and product scope.
- Multicamera 3D: promising but requires calibration, synchronisation and its own validation.
- Social feeds and public workout videos: do not improve assessment validity; increase privacy/moderation work.
- Automatic research reuse: consent must remain separate from product access.

## 25. Immediate build order

1. Define a side-view bodyweight squat contract with a coach.
2. Collect a small feasibility set with varied suitable and unsuitable recordings.
3. Build upload → pose → rep/tempo → evidence replay.
4. Evaluate on held-out people before adding correction claims.
5. Add guided camera placement and measure whether capture quality improves.
6. Expand one check and one exercise at a time.
7. Add optional learned/VLM components only when an identified failure and comparative evidence justify them.

## 26. Development operating model

Development proceeds in vertical, reviewable slices. A pull request is complete only when its code, tests, observability, migration impact and documentation are reviewable together. Avoid long-lived frontend, backend and model branches that integrate only at the end.

### Repository layout

```text
apps/
  web/                 React application and browser capture
  api/                 FastAPI HTTP application
workers/
  media/               Decode, normalisation and thumbnail jobs
  analysis/            Pose, segmentation and assessment jobs
packages/
  contracts/           Generated API client and shared schemas
  ui/                  RepWise design-system components
  exercise-contracts/  Versioned exercise/view/rule definitions
infra/                 Local containers and deployment configuration
tests/
  fixtures/            Licensed synthetic and consented test assets
  e2e/                 Cross-service browser journeys
docs/                  Decisions, runbooks and evaluation reports
```

The first implementation remains a modular monorepo. Boundaries above make ownership and tests clear without requiring independently deployed microservices.

### Branches, commits and pull requests

- Protect `main`; merge through pull requests after required checks pass.
- Use short branches such as `feat/upload-session`, `fix/vfr-timestamps` and `docs/retention-policy`.
- Use Conventional Commits: `feat(web): add upload review`, `test(api): cover duplicate submissions`.
- Keep a PR focused on one independently testable outcome. Split changes that mix infrastructure, unrelated refactors and product behaviour.
- Prefer squash merges so every merged PR becomes one understandable change on `main`.
- Require at least one reviewer for application changes and a qualified assessment reviewer for exercise-rule changes.
- Never merge generated secrets, raw participant recordings or unrestricted signed media URLs.

### Required pull-request evidence

Every PR includes:

1. Problem and user-visible outcome.
2. Scope and explicit non-goals.
3. Screenshots or recordings for UI changes; request/response examples for APIs.
4. Tests run and their results.
5. Privacy, security, accessibility and migration impact, using “none” only with a reason.
6. Rollout and rollback notes for runtime, schema, model or rule changes.
7. Linked issue, milestone and updated documentation where behaviour changed.

Draft PRs are encouraged for contract review. Do not use draft status to accumulate an unreviewable multi-week branch.

## 27. Definition of done and CI gates

A product slice is done when the supported happy path and declared failures work across the real boundary: browser, API, queue, worker, storage and report. A mocked UI alone is not end-to-end completion.

| Gate | Required evidence |
| --- | --- |
| Format and static analysis | Frontend lint/typecheck; backend lint/typecheck; schema and migration validation |
| Unit tests | State reducers, assessment features, temporal logic, permission checks and utility boundaries |
| Contract tests | OpenAPI compatibility, generated client freshness, exercise-contract schema validation and job payload compatibility |
| Integration tests | PostgreSQL, Redis, object storage and worker execution using isolated test resources |
| Browser E2E | Chromium on every PR; Firefox/WebKit and the supported mobile viewport set on scheduled/release runs |
| Media fixtures | Short deterministic clips covering rotation, variable frame rate, missing frames, corrupt input and unsuitable views |
| Accessibility | Automated checks plus keyboard/focus review for changed journeys |
| Security and privacy | Dependency/secret scanning, authorization tests, signed-URL scope, log redaction and deletion propagation |
| Performance | Bundle budget, API latency smoke checks and worker benchmark comparison for affected paths |
| Operations | Health checks, structured error category, metrics and a recovery path for new asynchronous behaviour |

Flaky tests are treated as defects. Quarantining one requires an owner, issue and expiry date; a quarantined release-gate test cannot count as passing.

## 28. Milestones and pull-request delivery plan

PR numbers below are sequencing identifiers, not pre-created GitHub numbers. Each PR should be merged before dependent work begins unless the dependency is an agreed contract that can be developed safely in parallel.

### Milestone A — Engineering foundation

| PR | Branch | Deliverable | Acceptance gate | Depends on |
| --- | --- | --- | --- | --- |
| PR-01 | `chore/monorepo-bootstrap` | Workspace layout, pinned toolchains, local environment example and task runner | Web/API placeholder health checks run locally; no secrets committed | — |
| PR-02 | `ci/quality-gates` | Lint, typecheck, unit, contract, build, dependency and secret checks | Required checks run on a sample PR and block an intentional failure | PR-01 |
| PR-03 | `feat/design-foundations` | Tokens, typography, accessible primitives and responsive app shell | Story/demo states pass keyboard, contrast and automated accessibility checks | PR-01 |
| PR-04 | `feat/api-foundation` | FastAPI app, configuration, PostgreSQL, Alembic, request IDs and structured errors | Fresh database migrates up/down; health/readiness distinguish dependencies | PR-01, PR-02 |
| PR-05 | `feat/local-services` | Redis, private object storage and worker containers for development/test | One command starts isolated services; smoke job completes and cleans up | PR-04 |

Milestone exit: a contributor can clone, configure, test and run the shell system from documented steps, and CI enforces the same baseline.

### Milestone B — Upload-first vertical slice

| PR | Branch | Deliverable | Acceptance gate | Depends on |
| --- | --- | --- | --- | --- |
| PR-06 | `feat/exercise-contracts` | Versioned squat/side-view contract schema, seed definition and validation CLI | Invalid landmarks, thresholds and unsupported checks fail validation | PR-04 |
| PR-07 | `feat/upload-api` | Authenticated upload initiation/completion/cancel with ownership, limits and idempotency | Duplicate completion produces one media asset/job; foreign access is denied | PR-05 |
| PR-08 | `feat/upload-web` | Exercise selection, file review, progress, cancellation and recoverable errors | Keyboard/mobile flow covers valid, oversized, cancelled and failed upload | PR-03, PR-07 |
| PR-09 | `feat/media-preflight` | Checksum, ffprobe validation, rotation/VFR-aware normalisation and audio removal | Fixture matrix preserves timestamp mapping and rejects corrupt media safely | PR-07 |
| PR-10 | `feat/pose-artifacts` | Pinned pose worker, landmark adapter, confidence/missingness and versioned artifact storage | Deterministic fixture output records model/checksum/schema metadata | PR-06, PR-09 |
| PR-11 | `feat/squat-segmentation` | Squat phase state machine, complete/partial reps and timestamp-based tempo | Held-out fixture tests meet proof-stage count/timing thresholds or abstain | PR-10 |
| PR-12 | `feat/evidence-report` | Immutable report schema, assessability states, replay mapping and report UI | Selecting a rep seeks to its evidence; missing metrics never display as zero | PR-08, PR-11 |
| PR-13 | `test/upload-report-journey` | Full browser-to-worker E2E suite, failure injection and initial runbook | Upload → process → report passes without service mocks; retry creates no duplicate | PR-12 |

Milestone exit: an authenticated internal user can upload a supported side-view squat and receive an evidence-linked count/tempo report, while unsuitable or failed media receives an actionable terminal state.

### Milestone C — Guided camera capture

| PR | Branch | Deliverable | Acceptance gate | Depends on |
| --- | --- | --- | --- | --- |
| PR-14 | `feat/camera-capabilities` | Permission recovery, device selection, recorder format negotiation and capability telemetry | Supported-device matrix documents actual formats and degraded paths | PR-03, PR-07 |
| PR-15 | `feat/capture-readiness` | Worker inference, framing/visibility/view/stability checks and instruction hysteresis | Difficult setup set measures false-ready rate; UI emits one stable prompt at a time | PR-06, PR-10, PR-14 |
| PR-16 | `feat/practice-rep` | Practice-rep state, suitability result and explicit exclusion from analysed set | Practice motion verifies coverage and cannot appear in final rep count | PR-11, PR-15 |
| PR-17 | `feat/recording-recovery` | Countdown, recording, interruption recovery, preview, discard and upload handoff | Backgrounding, track loss and active-exit cases preserve or discard exactly as shown | PR-14, PR-16 |
| PR-18 | `test/guided-capture-journey` | Physical-device E2E scenarios and camera accessibility checklist | Declared browsers/devices pass setup → practice → record → report and recovery cases | PR-17 |

Milestone exit: guided capture improves accepted-footage coverage on physical target devices without implying that readiness guarantees correct form.

### Milestone D — Private alpha

| PR | Branch | Deliverable | Acceptance gate | Depends on |
| --- | --- | --- | --- | --- |
| PR-19 | `feat/auth-sessions` | Production identity integration, verified accounts, secure sessions and role checks | Session rotation/revocation and every privileged route have authorization tests | PR-04 |
| PR-20 | `feat/history-retention` | Session history, raw-video expiry, deletion requests and tombstone propagation | Deletion test proves raw/derived assets are inaccessible and not recreated by retry | PR-12, PR-19 |
| PR-21 | `feat/report-feedback` | Wrong-count/tracking/advice feedback tied to analysis and rule versions | Feedback is auditable, permission-scoped and contains no public media URL | PR-12, PR-19 |
| PR-22 | `feat/pushup-contract` | Coach-reviewed side-view push-up rules, fixtures and report cues | Independent per-check evaluation passes its release contract; weak checks remain disabled | PR-06, PR-13 |
| PR-23 | `feat/curl-contract` | Coach-reviewed standing-curl rules, fixtures and report cues | Independent per-check evaluation passes its release contract; weak checks remain disabled | PR-06, PR-13 |
| PR-24 | `feat/annotation-review` | Restricted assignment, annotation, adjudication and release-approval workflow | Reviewers see assigned consented assets only; access and decisions are audited | PR-19, PR-21 |
| PR-25 | `feat/operations-dashboard` | Queue/failure/storage/cost metrics, retry controls, alerts and support grants | Injected worker/storage failures alert, recover and preserve deletion/ownership rules | PR-20, PR-24 |

Milestone exit: invited users can complete supported journeys with account security, history, correction feedback, deletion and operational support. Every enabled exercise check has versioned review evidence.

### Milestone E — Validated beta

| PR | Branch | Deliverable | Acceptance gate | Depends on |
| --- | --- | --- | --- | --- |
| PR-26 | `feat/progress-comparison` | Compatible-session trends with version, view and coverage context | Incompatible sessions cannot produce a misleading comparison | PR-20, PR-23 |
| PR-27 | `feat/export-privacy` | Account/report export and full account deletion orchestration | Export authorization and deletion completion are tested across all stores | PR-20 |
| PR-28 | `feat/release-controls` | Feature flags, canary cohorts, model/rule promotion and last-known-good rollback | A faulty check can be disabled without redeploying or altering historical reports | PR-24, PR-25 |
| PR-29 | `test/release-evaluation` | Participant-split evaluation, subgroup/failure report and adversarial report suite | Results meet section 20 gates with sample sizes/intervals, or scope is narrowed | PR-22, PR-23, PR-28 |
| PR-30 | `feat/beta-guardrails` | Quotas, usage ledger and optional payment path behind a disabled flag | Retries/rejections never duplicate usage or charges; limits fail transparently | PR-25, PR-29 |
| PR-31 | `release/validated-beta` | Production checklist, legal/privacy sign-off references, restore drill and rollback rehearsal | All enabled checks and supported devices have signed release evidence | PR-27–PR-30 |

Milestone exit: the beta scope is defined by measured evidence. Missing gates remove or narrow a capability; they do not become launch exceptions.

## 29. Issue and PR decomposition rules

Create one tracking issue per milestone and one issue per PR-sized outcome above. Each implementation issue must contain user value, acceptance criteria, failure cases, dependencies, instrumentation and out-of-scope items.

Split a planned PR when any of these becomes true:

- Review requires unrelated domain experts.
- The change introduces more than one independently deployable migration.
- UI review is blocked on an unsettled API or assessment contract.
- A model/rule evaluation cannot be reviewed separately from runtime plumbing.
- Rollback of one part should not roll back the other.

Do not split a vertical slice merely by file type. For example, the upload API and upload UI are separate above because each has a stable contract and meaningful independent tests; the report schema and evidence UI remain together because their correctness depends on the same evidence mapping.

## 30. Environments, fixtures and release flow

| Environment | Purpose | Data policy |
| --- | --- | --- |
| Local | Development with deterministic services and tiny fixtures | Synthetic or explicitly approved fixtures only |
| CI | Disposable integration and browser tests | Generated/synthetic media; no participant data |
| Staging | Release candidate, device testing and consented internal evaluation | Restricted consented data with production-like access controls |
| Production | Private alpha/beta users | Private-by-default user media and declared retention |

Promote immutable application images, exercise contracts and model artifacts; do not rebuild them per environment. Database migrations use expand/migrate/contract where a breaking schema transition is necessary. Roll out new assessment versions to internal recordings, then a canary cohort, then the supported population. Rollback disables new work while preserving the version needed to render historical reports.

Test media needs a manifest containing source/consent category, expected container properties, exercise/view, expected suitability, expected rep/phase annotations, permitted environments and expiry. Never copy an arbitrary customer recording into a fixture directory.

## 31. End-to-end acceptance journeys

Before each milestone exit, test the applicable journeys across real service boundaries:

1. New user selects squat, uploads valid video, leaves during processing, returns and opens a synchronised evidence report.
2. Duplicate submit/retry produces one billable analysis and one immutable report version.
3. Corrupt, oversized, unsupported-codec, ambiguous-subject and unsuitable-view videos fail with distinct recovery guidance.
4. Camera permission denial can be recovered without losing configured exercise context.
5. Guided capture handles cropped joints, wrong view, camera movement, practice failure, interruption, discard and successful recovery.
6. Partial reps and low-visibility intervals are excluded or marked uncertain without fabricated values.
7. Optional analysis components time out while the primary report completes safely.
8. A user cannot access another user’s upload, job, report, export, signed URL or deleted asset.
9. Video expiry/deletion removes replay and derived media while preserving only the metrics the user chose to retain.
10. A disabled rule stops new findings, historical reports retain their pinned interpretation, and rollback is observable.
11. Keyboard and screen-reader users can upload, follow processing, select a rep, inspect a finding and submit feedback.
12. Backup restoration recovers durable metadata without resurrecting expired or tombstoned media.

## 32. First development sprint

The first sprint should produce PR-01 through PR-04 and draft PR-06. Its reviewable outcome is a runnable, tested shell with one versioned squat assessment contract—not a simulated analysis dashboard.

Suggested order:

1. Create milestone/issue templates and protect `main`.
2. Merge the monorepo bootstrap and CI gates.
3. Merge design foundations and API/database foundation in parallel after contracts stabilise.
4. Review the squat contract with a qualified coach while infrastructure work continues.
5. Start PR-05 only after local configuration, migrations and CI are reproducible.

Sprint review demonstrates setup from a clean clone, CI enforcement, accessible foundation components, database migration/reversal, API health semantics and validation failures for an invalid exercise contract.

## 33. Primary technical references

Accessed 13 November 2026. Technical capabilities are sourced here; architecture choices and release targets above are recommendations.

- MediaPipe Pose Landmarker: https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker
- MediaPipe web integration and threading: https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker/web_js
- MediaPipe source/licence: https://github.com/google-ai-edge/mediapipe
- MMPose: https://github.com/open-mmlab/mmpose
- rtmlib: https://github.com/Tau-J/rtmlib
- Qwen3-VL: https://github.com/QwenLM/Qwen3-VL
- Fitness-AQA research and dataset restrictions: https://github.com/ParitoshParmar/Fitness-AQA

Check exact checkpoint, dependency and dataset terms before commercial inclusion; framework licensing alone is insufficient.
