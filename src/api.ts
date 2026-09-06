import type { AssessmentResult, Domain, DomainResult, Question } from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
const domainLabels: Record<string, Domain> = {
  abstract_reasoning: 'Abstract reasoning',
  deductive_logic: 'Deductive logic',
  numerical_reasoning: 'Numerical reasoning',
  verbal_reasoning: 'Verbal reasoning',
  visual_spatial_reasoning: 'Visual-spatial reasoning',
  working_memory: 'Working memory',
  processing_speed: 'Processing speed'
}

type ApiQuestion = { id: string; domain: string; type: Question['type']; prompt: string; options: string[]; helper?: string; visual?: string[] }
type SessionStart = { id: string; deadline_at: string; duration_seconds: number; question_count: number; domain_quota: number }
type SessionSummary = { deadline_at: string; duration_seconds: number; question_count: number; answered_count: number; status: string }
type ApiResult = {
  id: string
  session_id: string
  assessment_version: string
  score_version: string
  composite: number
  domain_scores: Record<string, number>
  domain_metrics: Record<string, { score: number; answered: number; correct: number; accuracy: number | null; median_response_time_ms: number | null; relative: string }>
  confidence: string
  quality: AssessmentResult['quality']
  answered_count: number
  question_count: number
  duration_seconds: number
  completed_at: string
  disclaimer: string
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 8000)
  try {
    const response = await fetch(`${API_BASE}${path}`, { ...init, signal: controller.signal, headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) } })
    if (!response.ok) {
      const body = await response.json().catch(() => ({})) as { detail?: string }
      throw new Error(body.detail || `IAQ API ${response.status}`)
    }
    return await response.json() as T
  } finally {
    window.clearTimeout(timeout)
  }
}

function normalize(item: ApiQuestion): Question {
  return { id: item.id, domain: domainLabels[item.domain] || 'Abstract reasoning', type: item.type, prompt: item.prompt, options: item.options, helper: item.helper, visual: item.visual }
}

function normalizeResult(result: ApiResult): AssessmentResult {
  const domainScores = {} as Record<Domain, number>
  const domainMetrics = {} as Record<Domain, DomainResult>
  Object.entries(result.domain_scores).forEach(([code, score]) => {
    const domain = domainLabels[code]
    if (!domain) return
    const metric = result.domain_metrics[code]
    domainScores[domain] = score
    domainMetrics[domain] = {
      score,
      answered: metric?.answered ?? 0,
      correct: metric?.correct ?? 0,
      accuracy: metric?.accuracy ?? null,
      medianResponseTimeMs: metric?.median_response_time_ms ?? null,
      relative: metric?.relative ?? 'within your profile'
    }
  })
  return {
    id: result.id,
    sessionId: result.session_id,
    assessmentVersion: result.assessment_version,
    scoreVersion: result.score_version,
    composite: result.composite,
    domainScores,
    domainMetrics,
    confidence: result.confidence,
    quality: result.quality,
    answeredCount: result.answered_count,
    questionCount: result.question_count,
    durationSeconds: result.duration_seconds,
    completedAt: result.completed_at,
    disclaimer: result.disclaimer
  }
}

export async function startRandomizedAssessment(): Promise<{ sessionId: string; question: Question; deadlineAt: string; durationSeconds: number; questionCount: number; answeredCount: number }> {
  const session = await request<SessionStart>('/assessments/iaq-cognitive/sessions', { method: 'POST', body: JSON.stringify({ assessment_version: 'IAQ-COG-0.3', mode: 'complete' }) })
  const started = await request<{ next_item: ApiQuestion }>(`/sessions/${session.id}/start`, { method: 'POST' })
  return { sessionId: session.id, question: normalize(started.next_item), deadlineAt: session.deadline_at, durationSeconds: session.duration_seconds, questionCount: session.question_count, answeredCount: 0 }
}

export async function resumeRandomizedAssessment(sessionId: string): Promise<{ sessionId: string; question: Question; deadlineAt: string; durationSeconds: number; questionCount: number; answeredCount: number }> {
  const session = await request<SessionSummary>(`/sessions/${sessionId}`)
  await request<{ status: string }>(`/sessions/${sessionId}/start`, { method: 'POST' })
  const next = await request<ApiQuestion & { complete?: boolean; expired?: boolean }>(`/sessions/${sessionId}/next-item`)
  if (next.expired || next.complete) throw new Error('This assessment session has ended.')
  return { sessionId, question: normalize(next), deadlineAt: session.deadline_at, durationSeconds: session.duration_seconds, questionCount: session.question_count, answeredCount: session.answered_count }
}

export async function saveAndGetNext(sessionId: string, question: Question, answer: string, order: number, responseTimeMs: number): Promise<Question | null> {
  await request(`/sessions/${sessionId}/responses`, { method: 'POST', headers: { 'Idempotency-Key': `${sessionId}:${question.id}` }, body: JSON.stringify({ item_id: question.id, answer, response_time_ms: responseTimeMs, presented_order: order }) })
  const next = await request<ApiQuestion & { complete?: boolean; expired?: boolean }>(`/sessions/${sessionId}/next-item`)
  if (next.expired) throw new Error('The assessment time has ended.')
  return next.complete ? null : normalize(next)
}

export async function finishAssessment(sessionId: string): Promise<AssessmentResult> {
  const result = await request<ApiResult>(`/sessions/${sessionId}/submit`, { method: 'POST' })
  return normalizeResult(result)
}

export async function getAssessmentResult(resultId: string): Promise<AssessmentResult> {
  return normalizeResult(await request<ApiResult>(`/results/${resultId}`))
}

export type ReportDelivery = {
  id: string
  result_id: string
  name: string
  email: string
  status: string
  requested_at: string
}

export async function requestReportDelivery(resultId: string, payload: { name: string; email: string; granted: boolean; age?: number }): Promise<ReportDelivery> {
  return request<ReportDelivery>(`/results/${resultId}/delivery`, { method: 'POST', body: JSON.stringify({ ...payload, consent_version: 'REPORT-DELIVERY-1.0' }) })
}
