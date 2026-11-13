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

## 26. Primary technical references

Accessed 13 November 2026. Technical capabilities are sourced here; architecture choices and release targets above are recommendations.

- MediaPipe Pose Landmarker: https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker
- MediaPipe web integration and threading: https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker/web_js
- MediaPipe source/licence: https://github.com/google-ai-edge/mediapipe
- MMPose: https://github.com/open-mmlab/mmpose
- rtmlib: https://github.com/Tau-J/rtmlib
- Qwen3-VL: https://github.com/QwenLM/Qwen3-VL
- Fitness-AQA research and dataset restrictions: https://github.com/ParitoshParmar/Fitness-AQA

Check exact checkpoint, dependency and dataset terms before commercial inclusion; framework licensing alone is insufficient.
