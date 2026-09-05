import type { Domain, Question } from './types'

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

type ApiQuestion = { id: string; domain: string; type: Question['type']; prompt: string; options: string[]; helper?: string }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 1200)
  try {
    const response = await fetch(`${API_BASE}${path}`, { ...init, signal: controller.signal, headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) } })
    if (!response.ok) throw new Error(`IAQ API ${response.status}`)
    return await response.json() as T
  } finally {
    window.clearTimeout(timeout)
  }
}

function normalize(item: ApiQuestion): Question {
  return { id: item.id, domain: domainLabels[item.domain] || 'Abstract reasoning', type: item.type, prompt: item.prompt, options: item.options, helper: item.helper }
}

export async function startRandomizedAssessment(): Promise<{ sessionId: string; question: Question }> {
  const session = await request<{ id: string }>('/assessments/iaq-cognitive/sessions', { method: 'POST', body: JSON.stringify({ assessment_version: 'IAQ-COG-0.3', mode: 'complete' }) })
  const started = await request<{ next_item: ApiQuestion }>(`/sessions/${session.id}/start`, { method: 'POST' })
  return { sessionId: session.id, question: normalize(started.next_item) }
}

export async function saveAndGetNext(sessionId: string, question: Question, answer: string, order: number): Promise<Question | null> {
  await request(`/sessions/${sessionId}/responses`, { method: 'POST', headers: { 'Idempotency-Key': `${sessionId}:${question.id}` }, body: JSON.stringify({ item_id: question.id, answer, response_time_ms: 10000, presented_order: order }) })
  const next = await request<ApiQuestion & { complete?: boolean }>(`/sessions/${sessionId}/next-item`)
  return next.complete ? null : normalize(next)
}

export async function finishAssessment(sessionId: string): Promise<{ domain_scores?: Record<string, number> }> {
  return request(`/sessions/${sessionId}/submit`, { method: 'POST' })
}
