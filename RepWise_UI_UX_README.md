# RepWise — UI/UX Design README

**Understand your form. Improve every rep.**

Version 1.0 · 13 November 2026

## Purpose

This is the design specification for RepWise, a premium exercise-video analysis application. Use it alongside `Exercise_Analysis_E2E_Plan.md`. That plan defines functional scope and evidence requirements; this README defines how those capabilities should look, feel and behave. The brand name and tagline are approved. The visual system below is the proposed direction for implementation.

Design a calm, precise and refined product that feels equally comfortable in a premium training studio and a personal gym session. Express luxury through typography, proportion, material-like colour, photography and careful interaction design. Keep the exercise and the user's video at the centre of attention.

## 1. Brand and visual direction

**Brand:** RepWise

**Tagline:** Understand your form. Improve every rep.

**Personality:** composed, knowledgeable, encouraging, discreet and precise.

**Visual concept: The private movement studio.** Warm ivory surfaces, midnight typography, restrained champagne accents, generous whitespace and crisp movement imagery. Camera and video-review environments use deep ink surfaces to frame footage. The result should feel premium without decorative clutter.

### Design principles

1. Give every screen one clear primary action.
2. Make the next step obvious during camera placement and recording.
3. Use evidence and readable measurements to establish trust.
4. Show uncertainty and unavailable assessments with the same care as successful results.
5. Reveal advanced detail progressively.
6. Use consistent alignment, spacing and components across the application.
7. Keep controls usable with sweaty hands, at arm's length and on small phones.
8. Reserve visual emphasis for decisions and useful feedback.

### Avoid

- Neon gradients, rainbow charts, glowing rings and animated particle backgrounds.
- Gold gradients, metallic textures, fake embossing and excessive glass effects.
- A grid of interchangeable cards on every screen.
- Tiny grey labels, excessive all-caps text and low-contrast gold body copy.
- Generic bodybuilding imagery, invented testimonials or unsupported accuracy claims.
- Decorative skeletons or numbers that imply real analysis before it exists.
- An invented global form score, safety badge or injury-risk percentage.

## 2. Three-colour brand system

| Role | Name | Hex | Primary use |
| --- | --- | --- | --- |
| Primary | Midnight Ink | `#151B1A` | Main typography, navigation, dark video environments, brand wordmark |
| Secondary | Warm Ivory | `#F7F4ED` | Main app canvas, light backgrounds, text on ink |
| Third / accent | Champagne Gold | `#C7A76C` | Primary buttons, selected highlights, active markers and limited chart emphasis |

These are the three brand colours. Supporting neutrals and semantic colours below have functional roles and must not become additional competing brand accents.

### Usage balance

For standard application screens, aim for approximately 75% ivory/light surface, 20% ink/text and 5% gold emphasis. This is a visual guideline, not a pixel requirement. Camera mode may be predominantly ink; gold stays restrained.

**Gold button rule:** use ink text on gold. Do not use white labels on gold. Gold on ivory is unsuitable for small text and cannot be the only boundary or state cue on an interactive control. Add an ink boundary, icon, label or sufficiently contrasting surface as needed.

### Supporting tokens

| Token | Value | Use |
| --- | --- | --- |
| Surface | `#FFFFFF` | Elevated content, input surfaces |
| Surface subtle | `#EFEAE0` | Quiet grouping and hover backgrounds |
| Border subtle | `#DDD8CE` | Decorative dividers only |
| Border control | `#817C72` | Input/control boundary where required |
| Text secondary | `#59615D` | Supporting body text on ivory/white |
| Text on dark secondary | `#C5CBC5` | Supporting text on ink |
| Gold hover | `#D3B985` | Primary-button hover |
| Gold pressed | `#B89558` | Primary-button press |
| Success | `#236346` | Readiness and successful checks |
| Warning | `#805214` | Capture issues requiring attention |
| Error | `#A33434` | Failures, destructive controls, recording indicator |
| Focus on light | `#151B1A` | Visible keyboard focus |
| Focus on dark | `#F7F4ED` | Visible keyboard focus |

Use semantic foregrounds on tested light tints and labelled/icon states. On video, use a solid or sufficiently opaque backing panel; never assume a text colour contrasts against arbitrary footage.

### CSS starting tokens

```css
:root {
  --rw-ink: #151b1a;
  --rw-ivory: #f7f4ed;
  --rw-gold: #c7a76c;
  --rw-surface: #ffffff;
  --rw-surface-subtle: #efeae0;
  --rw-text: var(--rw-ink);
  --rw-text-secondary: #59615d;
  --rw-border-subtle: #ddd8ce;
  --rw-border-control: #817c72;
  --rw-success: #236346;
  --rw-warning: #805214;
  --rw-error: #a33434;
  --rw-focus: var(--rw-ink);
  --rw-radius-control: 12px;
  --rw-radius-panel: 20px;
  --rw-radius-media: 24px;
  --rw-shadow-panel: 0 8px 30px rgb(21 27 26 / 5%);
  --rw-font-body: "Manrope", system-ui, sans-serif;
  --rw-font-editorial: "DM Serif Display", Georgia, serif;
}

[data-surface="dark"] {
  --rw-text: var(--rw-ivory);
  --rw-text-secondary: #c5cbc5;
  --rw-focus: var(--rw-ivory);
}
```

## 3. Typography and brand mark

**UI family:** Manrope, weights 400, 500, 600 and 700. Use for navigation, forms, reports and all controls.

**Editorial family:** DM Serif Display, regular. Use sparingly for the landing hero and occasional editorial headings; keep technical reporting in the UI family.

Self-host a licensed, subsetted font build with a robust fallback and `font-display: swap`. Include font licence files. Verify final font assets before distribution.

| Style | Desktop | Mobile | Treatment |
| --- | --- | --- | --- |
| Marketing hero | 64–76 px | 40–48 px | Serif, line-height 1.05–1.12 |
| Screen title | 32 px | 28 px | Sans, 600, line-height 1.2 |
| Section heading | 22–24 px | 20–22 px | Sans, 600 |
| Body | 16 px | 16 px | 400/500, line-height 1.5–1.65 |
| Supporting text | 14 px | 14 px | Secondary colour |
| Small metadata | 12–13 px | 12–13 px | Nonessential metadata only |
| Metric value | 32–40 px | 28–36 px | Sans, tabular numerals |

Limit reading width to about 65 characters for explanatory text. Avoid long passages in the serif. Use tabular numerals for timers and metrics to prevent horizontal jitter.

**Wordmark:** RepWise in a carefully spaced medium/semibold sans. Optional compact icon: a simple R or paired movement strokes, designed as a clean vector. It must remain recognisable at 24 px. A logo is a separate design deliverable; do not substitute an emoji or generic dumbbell icon as the final brand mark.

## 4. Layout, spacing and surfaces

- Spacing scale: 4, 8, 12, 16, 24, 32, 48, 64 and 96 px.
- Main content max width: 1280 px; editorial marketing sections may extend to 1440 px.
- Desktop navigation: approximately 232 px sidebar plus a flexible content region.
- Desktop content padding: 32–40 px. Tablet: 24 px. Phone: 16–20 px.
- Standard panels: 20 px radius, 24–32 px padding; mobile panels 16–20 px padding.
- Controls: 12 px radius, minimum 48 px height for primary form/button controls.
- Media: 24 px radius in regular screens; edge-to-edge where camera usability benefits.
- Use subtle borders or one soft shadow to indicate elevation. Avoid stacking both on every container.
- Prefer a strong page composition with a few intentional regions over many nested cards.
- Align titles, video edges, metrics and action groups to a shared grid.

### Responsive navigation

| Width / context | Navigation and composition |
| --- | --- |
| Under 768 px | Bottom navigation: Home, Exercises, History, Profile; prominent Analyse action on Home; Progress accessible from Home and History |
| 768–1023 px | Compact navigation rail or accessible drawer based on available content width |
| 1024 px and above | Sidebar: Overview, Analyse, Exercises, History, Progress; Settings/help lower in sidebar |
| Camera session | Dedicated full-viewport workspace; hide global navigation, preserve clear Exit control |

Breakpoints are starting points. Test 320 px through wide desktop, landscape phones and 200% zoom. Prevent sticky controls from covering focused fields or video controls. Honour safe-area insets.

## 5. Components and interaction states

### Buttons

- Primary: gold fill, ink label, clear contrasting boundary on light surfaces. Use for Analyse a set, Start countdown and View report.
- Secondary: ivory/white surface, ink text and visible control border.
- Tertiary: ink text with underline or clear hover/focus treatment; maintain a full touch target.
- Destructive: semantic red label or fill with tested contrast; use explicit verbs such as Delete video.
- Icon-only: accessible name and tooltip on pointer devices; never depend on tooltip for touch users.
- Implement default, hover, focus-visible, pressed, loading and disabled states. Loading retains the label, reserves width and blocks duplicate submission.

### Other shared components

- Text fields with persistent labels, optional helper text and inline validation.
- Search/filter controls, exercise selector and segmented capture-mode switch.
- Status badges with text and icon: Ready, Adjust camera, Processing, Partially assessed, Not assessable.
- Metric block with value, unit, source context and assessable-rep count.
- Video player with playback speed, skeleton toggle, timeline and accessible controls.
- Rep selector, finding panel, evidence link and feedback dialog.
- Upload drop zone with visible file-picker button and progress/cancel controls.
- Accessible modal, mobile bottom sheet, drawer, toast and inline alert.
- Skeleton placeholders for expected layout; do not animate fake analysis values.
- Empty state with one useful action; error state with reason, preserved input and recovery.

Use pill shapes for short badges and filters; keep buttons and major panels less rounded. Gold is not a success colour. Disabled controls need an adjacent explanation when the prerequisite is not obvious.

## 6. Screen specifications

### 6.1 Landing page

**Composition:** restrained header, editorial hero, authentic movement image/video, product preview and clear CTA.

- Header: wordmark, How it works, Exercises, optional Pricing, Sign in.
- Hero: approved tagline, one concise supporting sentence, primary Analyse a set, secondary See a sample report.
- Hero media: realistic training footage with one tasteful evidence annotation; example content labelled Sample report.
- Follow with three product steps: Set your view, Record your set, Review your movement.
- Show a substantial report preview, camera-guidance section, supported-exercise list, privacy explanation and FAQ.
- Footer: help, contact, privacy, terms and product identity.
- Publish prices, testimonials and performance claims only when real and approved.
- Keep text on its own readable region rather than over a busy athlete photograph.

### 6.2 Authentication and onboarding

- Minimal form with a quiet brand panel on desktop; single-column mobile layout.
- Explain verification and recovery with clear next steps; support password managers and accessible provider sign-in.
- Onboarding has few steps: goal/experience, units, short capture introduction, privacy preferences.
- Make optional questions visibly optional and skippable.
- Request camera access inside the capture flow, not at first sign-in.

### 6.3 Dashboard

- Header: “Your movement, in focus.” and a short description or greeting.
- Dominant action region: Analyse a set, with Record with camera and Upload video choices inside the next step.
- Recent sessions shown as spacious rows with thumbnail, exercise, date, reps, capture quality and report status.
- Small progress preview only when comparable data exists.
- First-use state: sample report plus filming guide. No invented stats, streaks or progress charts.
- Keep one hero action, recent work and a useful insight; avoid a wall of KPI tiles.

### 6.4 Exercise library and detail

- Search and filters for supported exercise/variant; display real supported scope.
- Cards use a consistent neutral-background demo image, exercise name and required view.
- Detail shows exercise variant, demo, camera illustration, what can be assessed and what cannot.
- CTA: Analyse this exercise.
- Upcoming exercises are clearly unavailable and never enter an unsupported analysis flow.

### 6.5 Session setup

- Compact step flow: Exercise → Capture → Review.
- Confirm exercise and variant; allow optional load, set number and target tempo.
- Use plain phase labels for tempo: Lowering, Bottom pause, Lifting, Top pause. Explain shorthand if offered.
- Capture choices are two explicit tiles: Use camera / Upload a video.
- Display the chosen assessment view and supported checks before continuing.

### 6.6 Guided camera setup — signature experience

**Desktop:** large video preview at left, approximately two-thirds width; calm instruction/readiness panel at right.

**Mobile:** preview uses available height; instruction panel and primary action remain reachable below. Keep controls outside the athlete's framing region.

- Top bar: exercise, required view, close/back control.
- Preview: thin corner framing guides; optional translucent target silhouette; visible camera selection.
- One prominent instruction at a time: “Move back until your feet are visible.”
- Supporting checklist: Full movement visible, Side view suitable, Camera stable.
- Replace vague completion percentages with named readiness conditions.
- Ready text: “Suitable for side-view assessment.”
- After phone placement, repeat stability check and prompt one practice rep.
- Practice-rep instruction is visually distinct and explicitly excluded from the set.
- Offer helper and solo instructions with a compact selector; both share the same quality gate.
- If checks cannot pass, explain why and offer Reposition camera or Save for replay only, where supported.
- Do not use “Perfect angle,” exact unmeasured degrees or a safety certification badge.

### 6.7 Recording

- Switch to ink surroundings with video unobstructed.
- Show a simple countdown, recording dot plus “Recording,” stable timer and a large Stop recording control.
- Skeleton overlay defaults to minimal/off if it obscures useful footage; allow user choice before the set.
- Display only important capture warnings with a labelled backing panel.
- No floating metric confetti, technique score or repeated coaching popups.
- If interrupted, preserve recoverable footage, identify the interruption and offer review/re-record.
- Exit during an active recording requires clear save/discard choices. Do not lose work silently.
- Provide optional spoken setup cues; never require audio to complete the flow.

### 6.8 Upload and preflight

- Elegant outlined drop area, visible Browse files button and concise accepted-format/limit text drawn from configuration.
- Selected file becomes a video preview with filename, duration, replace control and trim handles.
- Show progress based on real bytes; provide cancellation.
- Confirm exercise/variant and display view suitability after validation.
- Separate technical upload failures from unsuitable footage; use different recovery actions.
- Explain cloud processing and video retention before Analyse video.

### 6.9 Processing

- Show real stages: Checking video → Tracking movement → Reviewing reps → Preparing report.
- Current stage indicator and truthful queue status; do not imply every stage has equal duration.
- Use indeterminate progress where no trustworthy percentage exists.
- Explain that users can leave and find the report in History if the job is safely persisted.
- Cancellation, failure, partial completion and retry each have distinct states.
- Keep motion quiet and respect reduced-motion settings.

### 6.10 Report — signature experience

**Desktop:** report header, a large evidence video with a right-side selected-rep panel, then summary and detailed findings. Avoid making the video compete with many small charts.

**Mobile:** summary → video → rep selector → selected-rep findings → improvement priorities → detailed metrics.

- Header: exercise, date, variant, assessment view and quality status.
- Summary: complete reps, median lowering/lifting times, assessable count. Show partial reps separately.
- Video: play/pause, time, speed, fullscreen where supported and skeleton toggle.
- Rep timeline: discrete labelled segments; selecting a rep synchronises video, metrics and findings.
- Accessible alternative: next/previous rep and a list/table of reps; seeking cannot require dragging alone.
- Finding: observation, affected rep(s), evidence timestamp, explanation and one useful cue.
- Limit improvement priorities to three. Keep positive observations specific and evidence-based.
- Show “Not assessable” with a reason where necessary. Missing values are an em dash with explanation, never zero.
- Keep “9 of 10 reps assessable” visually close to its metric.
- Feedback action: “Something looks wrong?” with count, tracking and advice categories.
- Video expired/deleted state preserves the report where appropriate and clearly disables replay.
- Sharing/export only appear when implemented; private is the default.

### 6.11 Progress and history

- History defaults to a clean list; filters stay compact and resettable.
- Progress separates exercises and compatible variants/views.
- Use ink for the main trajectory, gold for selected points and semantic colours only when needed.
- Label axes and units, provide keyboard/touch inspection and an accessible data table.
- Show gaps for missing data; annotate analysis changes rather than suggesting false improvement.
- Show useful context such as target tempo and recording coverage.
- Comparison is unavailable when sessions cannot be compared meaningfully; explain why.

### 6.12 Profile, privacy, settings and optional billing

- Group Account, Preferences, Video storage, Privacy, Accessibility and optional Subscription.
- Show actual retention dates and explain video deletion versus full session deletion.
- Research consent is separate, optional and off by default.
- Delete dialogs name what will be deleted and whether metrics remain; destructive actions use explicit confirmation.
- Billing screens show real usage, limits, renewal terms and cancellation paths if monetisation is enabled.
- Keep upgrade prompts outside recording and evidence-review tasks.

### 6.13 Help, administration and annotation

- Help has filming examples, report interpretation and recoverable error guidance.
- Administration uses the same typography/tokens with denser tables and clear permissions.
- Model/rule releases show draft, evaluation, approved and disabled states.
- Annotation prioritises video, keyboard shortcuts, rep boundaries, visibility and rubric labels.
- Support users see metadata first; authorised video access is clearly scoped and logged.
- Privileged interfaces are separate from consumer navigation.

## 7. State and microcopy specification

| State | Recommended copy | Action |
| --- | --- | --- |
| Feet cropped | Move back until your feet are visible. | Continue adjusting |
| Wrong view | Turn sideways so we can assess this movement. | View placement guide |
| Suitable setup | Suitable for side-view assessment. | Try one practice rep |
| Stable view lost | The camera moved. Some reps may not be assessable. | Continue recording or stop |
| Multiple people | Keep one person in the assessment area. | Adjust view |
| Camera denied | Camera access is blocked. Enable it in your browser settings, or upload a video. | Try again / Upload video |
| Partial report | Some checks were unavailable for this recording. | See assessment limits |
| Occlusion | Your hip was hidden during this rep, so depth was not assessed. | Replay / Filming guide |
| No history | Your first set starts here. | Analyse a set |
| Video removed | Video replay is unavailable. Your saved measurements remain. | View metrics |

Use calm direct language. Avoid “bad form,” “unsafe,” “AI verified,” “perfect technique” and moralising failure messages. Technical model names and confidence internals belong in optional provenance details, not the main workflow.

## 8. Motion and sensory design

- Hover/press transitions: approximately 120–180 ms.
- Small panel transitions: 180–240 ms; avoid animating layout on every tracking update.
- Use opacity and small translations; no springs, bouncing metrics or endless shimmer.
- Readiness changes use a stable transition after the underlying dwell requirement passes.
- Respect reduced motion; remove nonessential movement and avoid flashing.
- Audio cues are optional and have visual equivalents.
- Haptics are progressive enhancement only where supported.
- Do not announce per-frame updates to screen readers; announce meaningful stage/status changes at a controlled rate.

## 9. Accessibility and interaction requirements

Target WCAG 2.2 AA and verify conformance during implementation; the specification alone does not establish it.

- Check text contrast: at least 4.5:1 for ordinary text, 3:1 for large text; relevant controls/focus indicators need appropriate non-text contrast.
- Pair every colour status with text/icon; charts also use labels or line patterns.
- Minimum 44×44 px effective touch targets; main gym-use controls preferably 48–56 px.
- Visible keyboard focus, logical tab order, skip navigation and accessible landmarks/headings.
- Trap and restore focus correctly in dialogs/drawers; Escape closes noncritical overlays.
- Persistent form labels, programmatic errors and clear required/optional indicators.
- Screen-reader names and state for camera, record, player, rep and upload controls.
- Caption demonstration videos; transcripts or written instructions accompany spoken guides.
- Support zoom/reflow, text enlargement and landscape; do not lock orientation.
- Ensure status panels, sticky CTAs and mobile navigation do not conceal focused controls.
- Make every scrub/trim operation possible through buttons or numeric controls as well as gestures.

## 10. Media and illustration direction

Use authentic, licensed exercise imagery with calm lighting and neutral backgrounds. Include varied bodies and realistic spaces. Preserve anatomy and avoid stylised imagery that teaches an incorrect movement.

Demo/camera illustrations must accurately show the required view and framing; use reviewed footage or precise illustrations. Use a consistent vector icon family with approximately 1.75–2 px strokes. Prefer simple camera-placement diagrams over decorative photos inside instructions.

Marketing images are separate from assessment evidence. Label mock reports and sample measurements. Obtain consent for identifiable athlete imagery and do not display customer recordings publicly by default.

## 11. Frontend implementation guidance

- React + TypeScript; central CSS variables and reusable semantic component variants.
- An accessible headless component foundation is suitable; style it deliberately rather than inheriting a generic dashboard aesthetic.
- Maintain separate components for camera guidance, recording, upload validation and report evidence.
- Use explicit typed states rather than loosely related boolean flags for capture and processing flows.
- Bind displayed readiness, progress and coverage to actual data; sample data is confined to labelled demos.
- Reserve media aspect ratios and content dimensions to prevent layout shifts.
- Lazy-load camera models and heavy analysis/player modules when needed; show download/error states.
- Keep inference off the main UI thread; throttle visual updates independently of inference.
- Store user preferences for overlay visibility and audio cues, respecting privacy choices.
- Design camera mode as its own operational workspace; full-app dark mode is a later enhancement unless separately scoped.

Suggested component names: `AppShell`, `ExerciseCard`, `AssessmentScope`, `CaptureModeSelector`, `CameraWorkspace`, `ReadinessChecklist`, `SetupInstruction`, `PracticeRepStep`, `RecordingControls`, `UploadPanel`, `AnalysisProgress`, `EvidencePlayer`, `RepTimeline`, `MetricBlock`, `FindingPanel`, `AssessmentCoverage`, `SessionList`, `ProgressChart`, `PrivacyControls`.

## 12. Design deliverables

1. Foundations: colour tokens, typography, spacing, responsive grids, elevation, iconography and imagery rules.
2. Component library with interaction, focus, disabled, loading, empty and error states.
3. High-fidelity desktop and mobile designs for every screen in section 6.
4. Clickable camera flow: permission → positioning → placed-camera check → practice rep → countdown → recording → review.
5. Clickable upload flow with unsuitable-footage and retry branches.
6. Interactive report prototype demonstrating timestamp/rep selection and unavailable-check states.
7. Accessibility notes, keyboard map, responsive behaviour and content specifications.
8. Engineering handoff with tokens, component contracts, asset licences and acceptance checklist.

Prototypes may use clearly labelled sample data; production screens must never present it as user analysis. Later features such as billing, sharing and coach review remain clearly scoped in the handoff.

## 13. Acceptance checklist

- [ ] RepWise name and approved tagline are used consistently.
- [ ] Midnight ink, warm ivory and champagne gold form the visible brand hierarchy.
- [ ] Gold buttons use readable ink labels and accessible boundaries/focus states.
- [ ] Typography and spacing are consistent; small-screen layouts retain breathing room.
- [ ] Every key screen has loading, empty, error and partial-data behaviour.
- [ ] Camera placement has concrete instructions and a practice-rep check.
- [ ] Readiness never implies guaranteed technique or safety.
- [ ] Recording controls remain reachable, readable and unobscured.
- [ ] Reports link findings to evidence and show assessment coverage.
- [ ] No fabricated form scores, testimonials, progress values or accuracy claims.
- [ ] Video timestamps and selected-rep states remain synchronised.
- [ ] Privacy/retention/deletion choices are explicit and understandable.
- [ ] Keyboard, touch, screen reader, contrast, zoom and reduced-motion checks pass.
- [ ] Camera flows are tested on physical supported phones, including interruptions.
- [ ] No navigation, marketing overlay or upgrade prompt interrupts recording.
- [ ] Optional/unimplemented features are absent or clearly unavailable.

## 14. Brief to give a designer or coding agent

> Design RepWise, a premium exercise-video analysis app, using the full specification in this README and the functional constraints in the E2E plan. Use midnight ink `#151B1A`, warm ivory `#F7F4ED` and champagne gold `#C7A76C` for primary actions and restrained emphasis. Pair Manrope UI typography with occasional DM Serif Display editorial headings. Prioritise generous spacing, confident typography, authentic movement imagery and accessible interactions. Make guided camera placement and evidence-linked reports the two signature experiences. Deliver complete responsive flows and real component states. Preserve assessment limits, private-by-default media and honest unavailable-data states throughout the interface.
