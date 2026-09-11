import type { AssessmentResult, Domain, DomainResult, Question } from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
const SUPABASE_URL = String(import.meta.env.VITE_SUPABASE_URL || '').replace(/\/$/, '')
const SUPABASE_ANON_KEY = String(import.meta.env.VITE_SUPABASE_ANON_KEY || '')
const domainLabels: Record<string, Domain> = {
  abstract_reasoning: 'Abstract reasoning',
  deductive_logic: 'Deductive logic',
  numerical_reasoning: 'Numerical reasoning',
  verbal_reasoning: 'Verbal reasoning',
  visual_spatial_reasoning: 'Visual-spatial reasoning',
  working_memory: 'Working memory',
  processing_speed: 'Processing speed'
}

type ApiQuestion = { id: string; domain: string; type: Question['type']; prompt: string; options?: string[]; helper?: string; visual?: string[]; render_type?: string; render_parameters?: Record<string, unknown>; image_url?: string; memory_response_type?: 'ordered_sequence' | 'cell_set'; memory_input_length?: number; memory_grid_size?: number }
type SessionStart = { id: string; deadline_at: string; duration_seconds: number; question_count: number; domain_quota: number; mode?: string; language?: string; practice?: boolean }
type SessionSummary = { deadline_at: string; duration_seconds: number; question_count: number; answered_count: number; status: string; mode?: string; practice?: boolean }
type ApiResult = {
  practice?: boolean
  status?: string
  message?: string
  id: string
  session_id: string
  assessment_version: string
  score_version: string
  score_kind?: string
  norm_version?: string | null
  composite: number | null
  iq_score?: number | null
  iq_score_kind?: string
  iq_score_label?: string
  iq_score_version?: string
  iq_score_scale?: string
  iq_score_method?: string
  official_iq_enabled?: boolean
  domain_scores: Record<string, number | null>
  domain_metrics: Record<string, { score: number | null; answered: number; correct: number; accuracy: number | null; median_response_time_ms: number | null; relative: string; interpretation_eligible?: boolean; evidence_note?: string }>
  confidence: string
  quality: AssessmentResult['quality']
  answered_count: number
  question_count: number
  duration_seconds: number
  completed_at: string
  disclaimer: string
  full_access?: boolean
  paywall?: { title: string; body: string; product_id: string }
}

export async function request<T>(path: string, init?: RequestInit, timeoutMs = 8000): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    const sessionToken = typeof window !== 'undefined' ? localStorage.getItem('iaq-session-token') : null
    const response = await fetch(`${API_BASE}${path}`, { ...init, signal: controller.signal, headers: { 'Content-Type': 'application/json', ...(sessionToken ? { 'X-IAQ-Session': sessionToken } : {}), ...(init?.headers || {}) } })
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
  const imageUrl = item.image_url ? (item.image_url.startsWith('http') ? item.image_url : `${API_BASE}${item.image_url}`) : undefined
  return { id: item.id, domain: domainLabels[item.domain] || 'Abstract reasoning', type: item.type, prompt: item.prompt, options: item.options || [], helper: item.helper, visual: item.visual, renderType: item.render_type, renderParameters: item.render_parameters, imageUrl, memoryResponseType: item.memory_response_type, memoryInputLength: item.memory_input_length, memoryGridSize: item.memory_grid_size }
}

function normalizeResult(result: ApiResult): AssessmentResult {
  const domainScores = {} as Record<Domain, number | null>
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
    scoreKind: result.score_kind,
    normVersion: result.norm_version,
    composite: result.composite,
    iqScore: result.iq_score,
    iqScoreKind: result.iq_score_kind,
    iqScoreLabel: result.iq_score_label,
    iqScoreVersion: result.iq_score_version,
    iqScoreScale: result.iq_score_scale,
    iqScoreMethod: result.iq_score_method,
    officialIqEnabled: result.official_iq_enabled,
    domainScores,
    domainMetrics,
    confidence: result.confidence,
    quality: result.quality,
    answeredCount: result.answered_count,
    questionCount: result.question_count,
    durationSeconds: result.duration_seconds,
    completedAt: result.completed_at,
    disclaimer: result.disclaimer,
    fullAccess: result.full_access,
    paywall: result.paywall
  }
}

export async function startRandomizedAssessment(): Promise<{ sessionId: string; question: Question; deadlineAt: string; durationSeconds: number; questionCount: number; answeredCount: number; practice: boolean }> {
  return startAssessmentWithOptions('complete', 'adult', 'en')
}

export async function startAssessmentWithOptions(mode: 'complete' | 'practice', ageBand: '15-17' | '18-22' | 'adult' | 'unknown', language: 'en' | 'id' = 'en'): Promise<{ sessionId: string; question: Question; deadlineAt: string; durationSeconds: number; questionCount: number; answeredCount: number; practice: boolean }> {
  const session = await request<SessionStart>('/assessments/iaq-cognitive/sessions', { method: 'POST', body: JSON.stringify({ assessment_version: 'IAQ-COG-0.3', mode, age_band: ageBand, language }) })
  const started = await request<{ next_item: ApiQuestion }>(`/sessions/${session.id}/start`, { method: 'POST' })
  return { sessionId: session.id, question: normalize(started.next_item), deadlineAt: session.deadline_at, durationSeconds: session.duration_seconds, questionCount: session.question_count, answeredCount: 0, practice: Boolean(session.practice || mode === 'practice') }
}

export async function resumeRandomizedAssessment(sessionId: string): Promise<{ sessionId: string; question: Question; deadlineAt: string; durationSeconds: number; questionCount: number; answeredCount: number; practice: boolean }> {
  const session = await request<SessionSummary>(`/sessions/${sessionId}`)
  await request<{ status: string }>(`/sessions/${sessionId}/start`, { method: 'POST' })
  const next = await request<ApiQuestion & { complete?: boolean; expired?: boolean }>(`/sessions/${sessionId}/next-item`)
  if (next.expired || next.complete) throw new Error('This assessment session has ended.')
  return { sessionId, question: normalize(next), deadlineAt: session.deadline_at, durationSeconds: session.duration_seconds, questionCount: session.question_count, answeredCount: session.answered_count, practice: Boolean(session.practice || session.mode === 'practice') }
}

export async function saveAndGetNext(sessionId: string, question: Question, answer: string, order: number, responseTimeMs: number): Promise<Question | null> {
  await request(`/sessions/${sessionId}/responses`, { method: 'POST', headers: { 'Idempotency-Key': `${sessionId}:${question.id}` }, body: JSON.stringify({ item_id: question.id, answer, response_time_ms: responseTimeMs, presented_order: Math.max(0, order) }) })
  const next = await request<ApiQuestion & { complete?: boolean; expired?: boolean }>(`/sessions/${sessionId}/next-item`)
  if (next.expired) throw new Error('The assessment time has ended.')
  return next.complete ? null : normalize(next)
}

export type PracticeCompletion = { practice: true; status: string; message: string }

export async function finishAssessment(sessionId: string): Promise<AssessmentResult | PracticeCompletion> {
  const result = await request<ApiResult & { practice?: boolean }>(`/sessions/${sessionId}/submit`, { method: 'POST' })
  if (result.practice) return { practice: true, status: result.status || 'complete', message: result.message || 'Practice complete.' }
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

export async function requestReportDelivery(resultId: string, payload: { name: string; email: string; granted: boolean; age?: number; guardian_consent_id?: string }): Promise<ReportDelivery> {
  return request<ReportDelivery>(`/results/${resultId}/delivery`, { method: 'POST', body: JSON.stringify({ ...payload, consent_version: 'REPORT-DELIVERY-1.0' }) })
}

export async function submitFeedback(payload: { message: string; page: string; email?: string }): Promise<{ accepted: boolean; id: string }> {
  return request<{ accepted: boolean; id: string }>('/feedback', { method: 'POST', body: JSON.stringify(payload) })
}

export type InterestItem = { id: string; label: string; dimension: string }
export type InterestResult = { id?: string; status: string; scores: Record<string, number>; code?: string | null; instrument?: string; instrument_version?: string; created_at?: string }

export async function getInterestQuestionnaire(): Promise<{ items: InterestItem[]; instructions: string; version: string }> {
  return request('/questionnaires/compass-v1')
}

export async function getInterestResult(): Promise<InterestResult> {
  return request('/me/interests')
}

export async function submitInterestResponses(responses: Record<string, number>, resultId?: string): Promise<InterestResult> {
  return request('/questionnaires/compass-v1/responses', { method: 'POST', body: JSON.stringify({ responses, result_id: resultId }) })
}

export type AIInterpretation = {
  id: string
  result_id: string
  kind: string
  status: string
  data_origin: string
  provider: string
  model: string
  prompt_version: string
  narrative: { what_stands_out: string[]; where_more_evidence: string[]; timing_context: string; next_step: string }
}

export async function getAIStatus(): Promise<{ enabled: boolean; configured: boolean; model: string | null; prompt_version: string; capabilities: string[] }> {
  return request('/ai/status')
}

export async function requestAIInterpretation(resultId: string): Promise<AIInterpretation> {
  return request(`/ai/results/${resultId}/interpretation`, { method: 'POST' })
}

export type AIDirectionContext = { slug: string; name: string; why_this_may_fit: string; try_next: string; caution: string }

export async function requestAIDirections(resultId: string): Promise<{ id: string; result_id: string; data_origin: string; provider: string; model: string; directions: AIDirectionContext[] }> {
  return request('/ai/directions', { method: 'POST', body: JSON.stringify({ result_id: resultId }) })
}

export type Certificate = { id: string; certificate_identifier: string; title: string; assessment_version: string; score_version: string; status: string; issued_at: string; verification_url: string }

export async function issueCertificate(resultId: string): Promise<Certificate> {
  return request('/certificates', { method: 'POST', body: JSON.stringify({ result_id: resultId }) })
}

export async function listCertificates(): Promise<Certificate[]> {
  return request<{ certificates: Certificate[] }>('/certificates').then((result) => result.certificates)
}

export async function verifyCertificate(identifier: string): Promise<{ valid: boolean; status: string; certificate_identifier: string; title?: string; assessment_version?: string; issued_at?: string }> {
  return request(`/certificates/verify/${encodeURIComponent(identifier)}`)
}

export type AccessUser = {
  id: string
  email: string
  display_name: string
  roles: string[]
  account_status: string
  age_band: string
  school_id?: string | null
  mfa_verified: boolean
}

export type Product = {
  id: string
  code: string
  name: string
  description: string
  price_id: string
  amount_minor: number
  currency: string
  active: boolean
}

export type Order = {
  id: string
  order_number: string
  purchaser_user_id: string
  beneficiary_user_id: string
  product_id: string
  product_snapshot: Product
  price_snapshot: { amount_minor: number; currency: string }
  total_minor: number
  currency: string
  status: string
  created_at: string
}

export async function devLogin(user: string): Promise<{ session_token: string; user: AccessUser; permissions: string[] }> {
  const result = await request<{ session_token: string; user: AccessUser; permissions: string[] }>('/auth/dev/login', { method: 'POST', body: JSON.stringify({ user }) })
  localStorage.setItem('iaq-session-token', result.session_token)
  localStorage.setItem('iaq-user', JSON.stringify(result.user))
  return result
}

export async function requestOtp(email: string): Promise<{ accepted: boolean; development_code?: string }> {
  return request('/auth/otp/request', { method: 'POST', body: JSON.stringify({ email }) })
}

export async function verifyOtp(email: string, code: string): Promise<{ session_token: string; user: AccessUser; permissions: string[] }> {
  const result = await request<{ session_token: string; user: AccessUser; permissions: string[] }>('/auth/otp/verify', { method: 'POST', body: JSON.stringify({ email, code }) })
  localStorage.setItem('iaq-session-token', result.session_token)
  localStorage.setItem('iaq-user', JSON.stringify(result.user))
  return result
}

export function supabaseConfigured(): boolean {
  return Boolean(SUPABASE_URL && SUPABASE_ANON_KEY)
}

async function supabaseRequest<T>(path: string, body: Record<string, unknown>): Promise<T> {
  if (!supabaseConfigured()) throw new Error('Supabase Auth is not configured for this deployment.')
  const response = await fetch(`${SUPABASE_URL}/auth/v1${path}`, { method: 'POST', headers: { apikey: SUPABASE_ANON_KEY, 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!response.ok) {
    const result = await response.json().catch(() => ({})) as { msg?: string; error_description?: string }
    throw new Error(result.msg || result.error_description || `Supabase Auth ${response.status}`)
  }
  return response.json() as Promise<T>
}

export async function requestSupabaseOtp(email: string): Promise<void> {
  await supabaseRequest('/otp', { email, create_user: true })
}

export async function verifySupabaseOtp(email: string, code: string): Promise<{ access_token: string }> {
  const result = await supabaseRequest<{ access_token: string }>('/verify', { email, token: code, type: 'email' })
  localStorage.setItem('iaq-session-token', result.access_token)
  return result
}

function base64Url(bytes: ArrayBuffer): string {
  return btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

export async function beginSupabaseGoogle(): Promise<void> {
  if (!supabaseConfigured()) throw new Error('Supabase Auth is not configured for this deployment.')
  const bytes = new Uint8Array(48)
  crypto.getRandomValues(bytes)
  const verifier = base64Url(bytes.buffer)
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier))
  localStorage.setItem('iaq-supabase-pkce-verifier', verifier)
  const redirect = `${window.location.origin}/auth/callback`
  window.location.assign(`${SUPABASE_URL}/auth/v1/authorize?provider=google&redirect_to=${encodeURIComponent(redirect)}&code_challenge=${encodeURIComponent(base64Url(digest))}&code_challenge_method=S256`)
}

export async function finishSupabaseCallback(): Promise<boolean> {
  if (!supabaseConfigured()) return false
  const query = new URLSearchParams(window.location.search)
  const code = query.get('code')
  if (code) {
    const verifier = localStorage.getItem('iaq-supabase-pkce-verifier')
    if (!verifier) throw new Error('The secure sign-in verifier is missing. Start sign-in again.')
    const result = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=pkce`, { method: 'POST', headers: { apikey: SUPABASE_ANON_KEY, 'Content-Type': 'application/json' }, body: JSON.stringify({ auth_code: code, code_verifier: verifier }) })
    if (!result.ok) throw new Error('Supabase could not finish the secure sign-in flow.')
    const session = await result.json() as { access_token?: string }
    if (!session.access_token) throw new Error('Supabase returned no access token.')
    localStorage.setItem('iaq-session-token', session.access_token)
    localStorage.removeItem('iaq-supabase-pkce-verifier')
    return true
  }
  const hash = new URLSearchParams(window.location.hash.replace(/^#/, ''))
  const token = hash.get('access_token')
  if (token) { localStorage.setItem('iaq-session-token', token); return true }
  return false
}

export async function logout(): Promise<void> {
  await request('/auth/logout', { method: 'POST' }).catch(() => undefined)
  localStorage.removeItem('iaq-session-token')
  localStorage.removeItem('iaq-user')
}

export async function getCurrentUser(): Promise<AccessUser> {
  return request<AccessUser>('/me').then((user) => ({ ...user, display_name: user.display_name || (user as AccessUser & { name?: string }).name || 'IAQ user' }))
}

export async function captureIdentity(payload: { email: string; display_name: string; age_band: '15-17' | '18-22' | 'adult' | 'unknown'; guardian_email?: string; granted: boolean }): Promise<{ user: AccessUser; consent_version: string; guardian_consent?: { id: string; status: string } }> {
  return request('/me/identity', { method: 'POST', body: JSON.stringify({ ...payload, consent_version: 'PILOT-DATA-1.0' }) })
}

export async function listProducts(): Promise<Product[]> {
  return request<{ products: Product[] }>('/products').then((result) => result.products)
}

export async function createOrder(productId: string, beneficiaryUserId?: string): Promise<Order> {
  return request<Order>('/orders', { method: 'POST', body: JSON.stringify({ product_id: productId, beneficiary_user_id: beneficiaryUserId }) })
}

export async function beginCheckout(orderId: string): Promise<{ order: Order; payment_attempt: { id: string; status: string; provider: string } | null; message: string }> {
  return request(`/orders/${orderId}/checkout`, { method: 'POST' })
}

export async function settleMockPayment(orderId: string): Promise<{ order: Order; verified: boolean; entitlement_created: boolean }> {
  return request(`/payments/mock/${orderId}/settle`, { method: 'POST' })
}

export async function getOrderStatus(orderId: string): Promise<{ order: Order; payment_attempt: { status: string } | null; entitlements: { code: string; status: string }[] }> {
  return request(`/orders/${orderId}/status`)
}

export type DatasetSummary = {
  available: boolean
  root: string
  student_sessions_use: boolean
  files: Array<{ file: string; dataset: string; domain: string; language?: string; records: number; unique_ids: number; families: number; missing_assets: number; review_status: Record<string, number>; production_eligible: number }>
  totals: { files: number; records: number; by_domain: Record<string, number>; missing_assets: number }
  review?: { reviewed_target_per_domain: number; by_domain: Record<string, { candidates: number; human_reviewed: number; in_review: number; changes_requested: number; draft: number; eligible_for_pilot: number }>; eligible_for_student_sessions: boolean; note: string }
}

export type DatasetCandidate = {
  id: string
  source_id: string
  source_dataset: string
  source_file: string
  domain: string
  item_family_id: string
  construct_id: string
  type: string
  prompt: string
  context?: string | null
  question?: string
  options: unknown[]
  answer?: unknown
  answer_index?: number
  rule?: string
  stimulus?: unknown
  image_path?: string
  asset_path?: string
  asset_exists?: boolean
  review_status: string
  lifecycle_status: string
  production_eligible: boolean
  commercial_use_approved: boolean
  content_version: number
  language: string
  data_origin: string
  provenance: { source_file?: string; source_url?: string; source_license?: string; generator?: string; seed?: number; stimulus_sha256?: string }
  review?: { review_count: number; approval_count: number; required_approvals: number; review_ready: boolean; reviews: Array<{ reviewer_id: string; decision: string; notes?: string }> }
}

export async function getDatasetSummary(): Promise<DatasetSummary> {
  return request<DatasetSummary>('/admin/dataset/summary', undefined, 30000)
}

export type DatasetAudit = { total: number; by_domain: Record<string, number>; unique_ids: number; unique_families: number; error_count: number; machine_integrity_passed: boolean; human_review_required: boolean; student_sessions_use: boolean }

export async function getDatasetAudit(): Promise<DatasetAudit> {
  return request<DatasetAudit>('/admin/dataset/audit', undefined, 30000)
}

export async function getDatasetPreview(params: { domain?: string; dataset?: string; limit?: number } = {}): Promise<{ items: DatasetCandidate[]; total: number; warning: string }> {
  const query = new URLSearchParams({ limit: String(params.limit || 24) })
  if (params.domain) query.set('domain', params.domain)
  if (params.dataset) query.set('dataset', params.dataset)
  return request(`/admin/dataset/preview?${query.toString()}`, undefined, 30000)
}

export async function getDatasetAsset(assetPath: string): Promise<string> {
  const sessionToken = typeof window !== 'undefined' ? localStorage.getItem('iaq-session-token') : null
  const normalizedPath = assetPath.replace(/^\/+/, '').replace(/^five_domains\//, '')
  const response = await fetch(`${API_BASE}/admin/dataset/assets/five_domains/${normalizedPath}`, { headers: sessionToken ? { 'X-IAQ-Session': sessionToken } : {} })
  if (!response.ok) throw new Error(`Dataset asset ${response.status}`)
  return URL.createObjectURL(await response.blob())
}

export async function reviewDatasetCandidate(itemId: string, payload: { decision: 'approve' | 'reject' | 'changes_requested'; notes: string; checks: Record<string, boolean> }): Promise<{ accepted: boolean; item: DatasetCandidate }> {
  return request(`/admin/dataset/items/${encodeURIComponent(itemId)}/review`, { method: 'POST', body: JSON.stringify({ ...payload, status: 'HUMAN_REVIEWED' }) })
}
