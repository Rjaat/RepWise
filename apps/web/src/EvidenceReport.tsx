import { useRef, useState } from 'react'

type Metric = {
  label: string
  unit: string
  state: 'assessed' | 'not_assessable' | 'uncertain'
  value: number | null
  reason?: string
}

type Rep = {
  index: number
  startSeconds: number
  endSeconds: number
  metrics: Metric[]
  observation: string
}

export type ReportData = {
  exercise: string
  date: string
  variant: string
  view: string
  completeReps: number
  partialReps: number
  assessableReps: number
  reps: Rep[]
}

const sampleReport: ReportData = {
  exercise: 'Bodyweight squat',
  date: 'Sample report',
  variant: 'Bodyweight',
  view: 'Side view',
  completeReps: 3,
  partialReps: 1,
  assessableReps: 2,
  reps: [
    {
      index: 1,
      startSeconds: 2.4,
      endSeconds: 5.1,
      observation: 'A complete repetition with a steady return to standing.',
      metrics: [
        { label: 'Lowering time', unit: 's', state: 'assessed', value: 1.2 },
        { label: 'Lifting time', unit: 's', state: 'assessed', value: 1.1 },
        {
          label: 'Visible depth',
          unit: '°',
          state: 'not_assessable',
          value: null,
          reason: 'Your hip was hidden during the lowest part of this rep.',
        },
      ],
    },
    {
      index: 2,
      startSeconds: 6.2,
      endSeconds: 9.4,
      observation: 'The lowering phase was slower than the first repetition.',
      metrics: [
        { label: 'Lowering time', unit: 's', state: 'assessed', value: 1.8 },
        { label: 'Lifting time', unit: 's', state: 'assessed', value: 1.2 },
        { label: 'Visible depth', unit: '°', state: 'assessed', value: 104 },
      ],
    },
    {
      index: 3,
      startSeconds: 10.3,
      endSeconds: 13.1,
      observation: 'Tracking was interrupted near the bottom position.',
      metrics: [
        { label: 'Lowering time', unit: 's', state: 'assessed', value: 1.3 },
        {
          label: 'Lifting time',
          unit: 's',
          state: 'uncertain',
          value: null,
          reason: 'The knee landmark was briefly hidden.',
        },
        {
          label: 'Visible depth',
          unit: '°',
          state: 'not_assessable',
          value: null,
          reason: 'The hip landmark was not visible.',
        },
      ],
    },
  ],
}

function formatTime(seconds: number) {
  return `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`
}

export function EvidenceReport({
  report = sampleReport,
}: {
  report?: ReportData
}) {
  const [selectedIndex, setSelectedIndex] = useState(0)
  const videoRef = useRef<HTMLVideoElement>(null)
  const selected = report.reps[selectedIndex]

  const selectRep = (index: number) => {
    setSelectedIndex(index)
    if (videoRef.current)
      videoRef.current.currentTime = report.reps[index].startSeconds
  }

  return (
    <article className="report" aria-labelledby="report-title">
      <header className="report__header">
        <div>
          <p className="report__eyebrow">{report.date}</p>
          <h1 id="report-title">{report.exercise} report</h1>
          <p>
            {report.variant} · {report.view}
          </p>
        </div>
        <span className="report__status">Partial report</span>
      </header>

      <section className="report__summary" aria-label="Set summary">
        <div>
          <strong>{report.completeReps}</strong>
          <span>Complete reps</span>
        </div>
        <div>
          <strong>{report.partialReps}</strong>
          <span>Partial reps</span>
        </div>
        <div>
          <strong>
            {report.assessableReps} of {report.completeReps}
          </strong>
          <span>Reps assessable</span>
        </div>
      </section>

      <div className="report__evidence-grid">
        <section className="evidence-video" aria-labelledby="evidence-heading">
          <h2 id="evidence-heading">Evidence replay</h2>
          <video ref={videoRef} controls aria-label="Exercise evidence video" />
          <p>Private recording · Select a rep to seek to its evidence.</p>
        </section>

        <section className="rep-detail" aria-live="polite">
          <p className="report__eyebrow">Selected evidence</p>
          <h2>Rep {selected.index}</h2>
          <p>
            {formatTime(selected.startSeconds)}–
            {formatTime(selected.endSeconds)}
          </p>
          <p>{selected.observation}</p>
          <dl>
            {selected.metrics.map((metric) => (
              <div key={metric.label}>
                <dt>{metric.label}</dt>
                <dd>
                  {metric.value === null ? (
                    <>
                      <span aria-label="Not assessable">—</span>
                      <small>{metric.reason}</small>
                    </>
                  ) : (
                    `${metric.value} ${metric.unit}`
                  )}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      </div>

      <section className="rep-selector" aria-labelledby="reps-heading">
        <div className="rep-selector__heading">
          <div>
            <p className="report__eyebrow">Evidence timeline</p>
            <h2 id="reps-heading">Review each rep</h2>
          </div>
          <div>
            <button
              type="button"
              onClick={() => selectRep(Math.max(0, selectedIndex - 1))}
              disabled={selectedIndex === 0}
            >
              Previous rep
            </button>
            <button
              type="button"
              onClick={() =>
                selectRep(Math.min(report.reps.length - 1, selectedIndex + 1))
              }
              disabled={selectedIndex === report.reps.length - 1}
            >
              Next rep
            </button>
          </div>
        </div>
        <div className="rep-selector__buttons">
          {report.reps.map((rep, index) => (
            <button
              key={rep.index}
              type="button"
              aria-pressed={index === selectedIndex}
              onClick={() => selectRep(index)}
            >
              <strong>Rep {rep.index}</strong>
              <span>{formatTime(rep.startSeconds)}</span>
            </button>
          ))}
        </div>
      </section>
    </article>
  )
}
