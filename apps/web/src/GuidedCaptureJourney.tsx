import { useState } from 'react'

import { CameraSetup } from './CameraSetup'
import { EvidenceReport } from './EvidenceReport'
import { RecordingSession } from './RecordingSession'

const ready = {
  ready: true,
  instruction: 'Suitable for side-view assessment.',
  checks: {
    full_movement_visible: true,
    side_view_suitable: true,
    camera_stable: true,
  },
}

export function GuidedCaptureJourney({
  countdownSeconds = 3,
}: {
  countdownSeconds?: number
}) {
  const [stage, setStage] = useState<'setup' | 'record' | 'report'>('setup')

  if (stage === 'setup') {
    return (
      <CameraSetup
        readiness={ready}
        onPracticeComplete={() => setStage('record')}
      />
    )
  }
  if (stage === 'record') {
    return (
      <RecordingSession
        countdownSeconds={countdownSeconds}
        onUseRecording={() => setStage('report')}
      />
    )
  }
  return <EvidenceReport />
}
