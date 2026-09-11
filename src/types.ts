export type Role = 'student' | 'counselor' | 'admin'

export type Domain =
  | 'Abstract reasoning'
  | 'Deductive logic'
  | 'Numerical reasoning'
  | 'Verbal reasoning'
  | 'Visual-spatial reasoning'
  | 'Working memory'
  | 'Processing speed'

export type Question = {
  id: string
  domain: Domain
  type: 'choice' | 'sequence' | 'memory' | 'speed'
  prompt: string
  helper?: string
  options: string[]
  // Visual items use a list for legacy deterministic stimuli. Imported
  // working-memory records may carry a structured study stimulus instead.
  visual?: string[] | Record<string, unknown>
  renderType?: string
  renderParameters?: Record<string, unknown>
  imageUrl?: string
  memoryResponseType?: 'ordered_sequence' | 'cell_set'
  memoryInputLength?: number
  memoryGridSize?: number
}

export type Major = {
  name: string
  family: string
  fit: number
  readiness: number
  feasibility: 'Ready to explore' | 'Build evidence' | 'Needs preparation'
  confidence: number
  reason: string
  tags: string[]
  accent: string
}

export type Profile = {
  name: string
  completed: boolean
  consented: boolean
  role: Role
  lastAssessment: string
  nextAssessment: string
  strengths: Domain[]
  scores: Record<Domain, number | null>
  composite?: number | null
  iqScore?: number | null
  confidence?: string
  lastResult?: AssessmentResult
}

export type DomainResult = {
  score: number | null
  answered: number
  correct: number
  accuracy: number | null
  medianResponseTimeMs: number | null
  relative: string
}

export type AssessmentResult = {
  id: string
  sessionId: string
  assessmentVersion: string
  scoreVersion: string
  scoreKind?: string
  normVersion?: string | null
  composite: number | null
  iqScore?: number | null
  iqScoreKind?: string
  iqScoreLabel?: string
  iqScoreVersion?: string
  iqScoreScale?: string
  iqScoreMethod?: string
  officialIqEnabled?: boolean
  domainScores: Record<Domain, number | null>
  domainMetrics: Record<Domain, DomainResult>
  confidence: string
  quality: {
    status: string
    rapidGuessingItems?: number
    fatigueProbability?: number
    warnings?: string[]
  }
  answeredCount: number
  questionCount: number
  durationSeconds: number
  completedAt: string
  disclaimer: string
  fullAccess?: boolean
  paywall?: {
    title: string
    body: string
    product_id: string
  }
}
