import { useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts'
import { Link, NavLink, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { alternatives, domainMeta, domains, initialScores, majors, questions, recommendations } from './data'
import { captureIdentity, finishAssessment, getAIStatus, getInterestResult, requestAIDirections, requestAIInterpretation, requestReportDelivery, resumeRandomizedAssessment, saveAndGetNext, startRandomizedAssessment, submitFeedback, type AIDirectionContext, type AIInterpretation, type InterestResult } from './api'
import { AccountSettings, AuthCallback, AuthLogin, Billing, Checkout, PaymentPage, Pricing } from './access'
import { CertificateVerification, Certificates, InterestAssessment, LegalPage, PublicInfoPage } from './product'
import type { AssessmentResult, Domain, Major, Profile, Question, Role } from './types'

const initialProfile: Profile = {
  name: 'Ari Pratama', completed: false, consented: true, role: 'student', lastAssessment: '', nextAssessment: 'After enough new evidence', strengths: [], scores: initialScores
}

const ASSESSMENT_SESSION_KEY = 'iaq-active-assessment-session'

const searchPages = [
  { to: '/', label: 'Overview', description: 'Start here and see your latest profile.' },
  { to: '/assess', label: 'Take a test', description: 'Start the 35-minute assessment.' },
  { to: '/results', label: 'Your results', description: 'Read your seven-domain report.' },
  { to: '/compass', label: 'Explore directions', description: 'Compare possible next directions.' },
  { to: '/tracker', label: 'Your progress', description: 'Review evidence and activity.' },
  { to: '/methodology', label: 'Methodology', description: 'Understand the IAQ approach and limits.' },
]

function AppBootLoader({ active }: { active: boolean }) {
  return <AnimatePresence>{active && <motion.div className="app-boot-loader" initial={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: .28 }}><Brand /><span className="boot-line"><i /></span><small>Preparing your workspace</small></motion.div>}</AnimatePresence>
}

function ScrollProgress() {
  const [progress, setProgress] = useState(0)
  useEffect(() => {
    const update = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight
      setProgress(max > 0 ? (window.scrollY / max) * 100 : 0)
    }
    update()
    window.addEventListener('scroll', update, { passive: true })
    window.addEventListener('resize', update)
    return () => { window.removeEventListener('scroll', update); window.removeEventListener('resize', update) }
  }, [])
  return <div className="scroll-progress" aria-hidden="true"><span style={{ width: `${progress}%` }} /></div>
}

function CursorFollower() {
  const cursor = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const onMove = (event: PointerEvent) => { if (cursor.current) cursor.current.style.transform = `translate3d(${event.clientX}px, ${event.clientY}px, 0)` }
    window.addEventListener('pointermove', onMove, { passive: true })
    return () => window.removeEventListener('pointermove', onMove)
  }, [])
  return <div ref={cursor} className="cursor-follower" aria-hidden="true" />
}

function BackToTop() {
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    const update = () => setVisible(window.scrollY > 500)
    window.addEventListener('scroll', update, { passive: true })
    return () => window.removeEventListener('scroll', update)
  }, [])
  return <AnimatePresence>{visible && <motion.button className="back-to-top" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 10 }} onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} aria-label="Back to top">↑</motion.button>}</AnimatePresence>
}

function ThemeToggle() {
  const [dark, setDark] = useState(() => localStorage.getItem('iaq-theme') === 'dark')
  const toggle = () => {
    const next = !dark
    setDark(next)
    document.documentElement.dataset.theme = next ? 'dark' : 'light'
    localStorage.setItem('iaq-theme', next ? 'dark' : 'light')
  }
  return <button className="theme-toggle" onClick={toggle} aria-label={dark ? 'Use light mode' : 'Use dark mode'} aria-pressed={dark}><span>{dark ? '☼' : '◐'}</span><small>{dark ? 'Light' : 'Dark'}</small></button>
}

function AnimatedNumber({ value }: { value: number }) {
  const [display, setDisplay] = useState(0)
  useEffect(() => {
    const started = performance.now()
    const duration = 650
    let frame = 0
    const tick = (now: number) => {
      const progress = Math.min(1, (now - started) / duration)
      setDisplay(Math.round(value * (1 - Math.pow(1 - progress, 3))))
      if (progress < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [value])
  return <>{display}</>
}

function GlobalSearch({ compact = false }: { compact?: boolean }) {
  const [query, setQuery] = useState('')
  const matches = searchPages.filter((page) => `${page.label} ${page.description}`.toLowerCase().includes(query.toLowerCase())).slice(0, 4)
  return <div className={`global-search ${compact ? 'compact' : ''}`}><label><span aria-hidden="true">⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search IAQ" aria-label="Search IAQ" /></label>{query && <div className="search-results" role="listbox" aria-label="Search results">{matches.length ? matches.map((page) => <Link key={page.to} to={page.to} onClick={() => setQuery('')} role="option"><strong>{page.label}</strong><span>{page.description}</span></Link>) : <div className="search-empty">No IAQ pages match “{query}”.</div>}</div>}</div>
}

function FeedbackButton() {
  const [open, setOpen] = useState(false)
  const [message, setMessage] = useState('')
  const [status, setStatus] = useState('')
  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    try { await submitFeedback({ message, page: window.location.pathname }); setStatus('Thanks — your note was saved.'); setMessage('') } catch { setStatus('We could not save that note right now.') }
  }
  return <><button className="feedback-trigger" onClick={() => setOpen(true)} aria-label="Send feedback">Feedback</button>{open && <div className="modal-backdrop" role="presentation"><div className="feedback-modal" role="dialog" aria-modal="true" aria-labelledby="feedback-title"><button className="modal-close" onClick={() => setOpen(false)} aria-label="Close feedback">×</button><div className="eyebrow">Help us improve IAQ</div><h2 id="feedback-title">What should feel better?</h2><p>Tell us what was confusing, useful, or missing. Do not include private assessment answers.</p><form onSubmit={submit}><label>Feedback<textarea value={message} onChange={(event) => setMessage(event.target.value)} required minLength={4} rows={4} placeholder="I noticed…" /></label><button className="button primary" disabled={!message.trim()}>Send feedback <span>→</span></button>{status && <span className="feedback-status" role="status">{status}</span>}</form></div></div>}</>
}

function NotFound() {
  return <div className="not-found"><div className="eyebrow">404 / page not found</div><h1>That page is not here.<br /><em>Let’s get you back.</em></h1><p>The link may be old or the page may have moved.</p><Link className="button primary" to="/">Back to overview <span>→</span></Link></div>
}

function App() {
  const location = useLocation()
  const [booting, setBooting] = useState(true)
  useEffect(() => {
    const savedTheme = localStorage.getItem('iaq-theme')
    if (savedTheme) document.documentElement.dataset.theme = savedTheme
    const timer = window.setTimeout(() => setBooting(false), 320)
    return () => window.clearTimeout(timer)
  }, [])
  useEffect(() => { window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior }) }, [location.pathname])
  const [profile, setProfile] = useState<Profile>(() => {
    try { return JSON.parse(localStorage.getItem('iaq-profile') || '') as Profile } catch { return initialProfile }
  })
  const [savedMajors, setSavedMajors] = useState<string[]>(() => JSON.parse(localStorage.getItem('iaq-saved-majors') || '[]'))
  const [assessmentComplete, setAssessmentComplete] = useState(() => localStorage.getItem('iaq-assessment-complete') === 'true')

  useEffect(() => { localStorage.setItem('iaq-profile', JSON.stringify(profile)) }, [profile])
  useEffect(() => { localStorage.setItem('iaq-saved-majors', JSON.stringify(savedMajors)) }, [savedMajors])
  useEffect(() => { localStorage.setItem('iaq-assessment-complete', String(assessmentComplete)) }, [assessmentComplete])

  const toggleMajor = (name: string) => setSavedMajors((items) => items.includes(name) ? items.filter((item) => item !== name) : [...items, name])
  const completeAssessment = (result: AssessmentResult) => {
    setProfile((current) => ({ ...current, completed: true, lastAssessment: new Date(result.completedAt).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }), composite: result.composite, confidence: result.confidence, scores: result.domainScores, strengths: [...domains].filter((domain) => result.domainScores[domain] != null).sort((a, b) => (result.domainScores[b] ?? -1) - (result.domainScores[a] ?? -1)).slice(0, 2), lastResult: result }))
    setAssessmentComplete(true)
  }

  const quietMode = location.pathname === '/assess/session'
  return <><AppBootLoader active={booting} /><ScrollProgress /><CursorFollower /><Routes>
    <Route path="/welcome" element={<PublicSite />} />
    <Route path="/how-it-works" element={<PublicInfoPage kind="method" />} />
    <Route path="/assessments" element={<StudentAppShell profile={profile}><AssessLanding /></StudentAppShell>} />
    <Route path="/for-schools" element={<PublicInfoPage kind="schools" />} />
    <Route path="/schools" element={<PublicInfoPage kind="schools" />} />
    <Route path="/about" element={<PublicInfoPage kind="about" />} />
    <Route path="/sample-report" element={<PublicInfoPage kind="sample" />} />
    <Route path="/help" element={<PublicInfoPage kind="help" />} />
    <Route path="/auth/login" element={<AuthLogin />} />
    <Route path="/auth/register" element={<AuthLogin />} />
    <Route path="/auth/callback" element={<AuthCallback />} />
    <Route path="/auth/verify" element={<AuthCallback />} />
    <Route path="/auth/onboarding" element={<AuthLogin />} />
    <Route path="/auth/invitation" element={<AuthLogin />} />
    <Route path="/auth/guardian-consent" element={<AuthLogin />} />
    <Route path="/auth/mfa/enroll" element={<AuthCallback />} />
    <Route path="/auth/mfa/challenge" element={<AuthCallback />} />
    <Route path="/auth/error" element={<AuthCallback />} />
    <Route path="/pricing" element={<StudentAppShell profile={profile}><Pricing /></StudentAppShell>} />
    <Route path="/checkout/:productId" element={<StudentAppShell profile={profile}><Checkout /></StudentAppShell>} />
    <Route path="/checkout/:orderId/pay" element={<StudentAppShell profile={profile}><PaymentPage /></StudentAppShell>} />
    <Route path="/payment/:orderId/:state" element={<StudentAppShell profile={profile}><PaymentPage /></StudentAppShell>} />
    <Route path="/app/billing" element={<StudentAppShell profile={profile}><Billing /></StudentAppShell>} />
    <Route path="/app/settings/profile" element={<StudentAppShell profile={profile}><AccountSettings /></StudentAppShell>} />
    <Route path="/app/settings/security" element={<StudentAppShell profile={profile}><AccountSettings /></StudentAppShell>} />
    <Route path="/app/settings/privacy" element={<StudentAppShell profile={profile}><Privacy /></StudentAppShell>} />
    <Route path="/app/settings/sessions" element={<StudentAppShell profile={profile}><AccountSettings /></StudentAppShell>} />
    <Route path="/" element={<StudentAppShell profile={profile}><Home profile={profile} savedMajors={savedMajors} /></StudentAppShell>} />
    <Route path="/assess" element={<StudentAppShell profile={profile}><AssessLanding /></StudentAppShell>} />
    <Route path="/assess/session" element={<Assessment onComplete={completeAssessment} />} />
    <Route path="/compass" element={<StudentAppShell profile={profile}><Compass profile={profile} savedMajors={savedMajors} toggleMajor={toggleMajor} /></StudentAppShell>} />
    <Route path="/interests" element={<StudentAppShell profile={profile}><InterestAssessment resultId={profile.lastResult?.id} /></StudentAppShell>} />
    <Route path="/certificates" element={<StudentAppShell profile={profile}><Certificates resultId={profile.lastResult?.id} /></StudentAppShell>} />
    <Route path="/verify" element={<StudentAppShell profile={profile}><CertificateVerification /></StudentAppShell>} />
    <Route path="/tracker" element={<StudentAppShell profile={profile}><Tracker savedMajors={savedMajors} /></StudentAppShell>} />
    <Route path="/results" element={<StudentAppShell profile={profile}><Results profile={profile} savedMajors={savedMajors} toggleMajor={toggleMajor} /></StudentAppShell>} />
    <Route path="/school" element={<CounselorAppShell><School /></CounselorAppShell>} />
    <Route path="/admin" element={<AdminAppShell><Admin /></AdminAppShell>} />
    <Route path="/methodology" element={<StudentAppShell profile={profile}><Methodology /></StudentAppShell>} />
    <Route path="/privacy" element={<StudentAppShell profile={profile}><Privacy /></StudentAppShell>} />
    <Route path="/terms" element={<StudentAppShell profile={profile}><LegalPage title="Terms for using IAQ" body="IAQ is an experimental educational product. Use it for reflection and planning, not for diagnosis, selection, or high-stakes decisions." /></StudentAppShell>} />
    <Route path="/refunds" element={<StudentAppShell profile={profile}><LegalPage title="Refunds and access" body="Purchases, entitlements, and refund handling depend on the provider and order terms shown at checkout. Contact IAQ support with your order number." /></StudentAppShell>} />
    <Route path="*" element={<NotFound />} />
  </Routes>{!quietMode && <><BackToTop /><FeedbackButton /></>}</>
}

const studentNav = [
  { to: '/', label: 'Overview', icon: '⌂', end: true },
  { to: '/assess', label: 'Take a test', icon: '◈' },
  { to: '/results', label: 'Your results', icon: '↗' },
  { to: '/compass', label: 'Explore directions', icon: '✦' },
  { to: '/tracker', label: 'Your progress', icon: '◒' }
]

function pageName(pathname: string) {
  const names: Record<string, string> = { '/': 'Overview', '/assess': 'Take a test', '/compass': 'Explore directions', '/interests': 'Your interests', '/certificates': 'Certificates', '/tracker': 'Your progress', '/results': 'Your results', '/school': 'Overview', '/admin': 'Overview', '/methodology': 'Help & Methodology', '/privacy': 'Privacy' }
  return names[pathname] || pathname.slice(1).replaceAll('-', ' ')
}

function Brand({ to = '/' }: { to?: string }) {
  return <Link to={to} className="brand"><span className="brand-mark">i</span><span>IAQ</span><span className="brand-dot">·</span></Link>
}

function WorkspaceSwitcher({ active }: { active: string }) {
  return <div className="workspace-switcher"><Brand /><span className="workspace-divider">/</span><details><summary>{active}<span className="workspace-chevron">⌄</span></summary><div className="workspace-menu"><Link to="/">Student Profile</Link><Link to="/school">Counselor Workspace</Link><Link to="/admin">Administration</Link><Link to="/welcome">Public Website</Link></div></details></div>
}

function ProfileMenu({ profile, label }: { profile?: Profile; label: string }) {
  return <details className="profile-menu"><summary><div className="avatar">AP</div><div><strong>{profile?.name || 'Ari Pratama'}</strong><span>{label}</span></div><span className="profile-chevron">⌄</span></summary><div className="profile-popover"><Link to="/app/settings/profile">Account</Link><Link to="/app/billing">Plan & billing</Link><Link to="/methodology">Help & Methodology</Link><Link to="/privacy">Privacy</Link><Link to="/auth/login">Switch account</Link></div></details>
}

function StudentAppHeader({ profile }: { profile: Profile }) {
  const [menuOpen, setMenuOpen] = useState(false)
  return <header className="student-header"><div className="student-header-inner"><WorkspaceSwitcher active="Student Profile" /><button className="student-menu-toggle" onClick={() => setMenuOpen((value) => !value)} aria-expanded={menuOpen} aria-controls="student-navigation">Menu</button><nav id="student-navigation" className={`student-nav ${menuOpen ? 'is-open' : ''}`} aria-label="Student navigation">{studentNav.map((item) => <NavLink key={item.to} to={item.to} end={item.end} onClick={() => setMenuOpen(false)} className={({ isActive }) => `student-nav-link ${isActive ? 'active' : ''}`}>{item.label}</NavLink>)}</nav><div className="student-utilities"><GlobalSearch compact /><ThemeToggle /><ProfileMenu profile={profile} label="Student profile" /></div></div></header>
}

function MobileStudentNavigation() {
  const mobileNav = [studentNav[0], studentNav[1], studentNav[3], studentNav[4]]
  return <nav className="mobile-student-nav" aria-label="Mobile student navigation">{mobileNav.map((item) => <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => `mobile-student-link ${isActive ? 'active' : ''}`}><span>{item.icon}</span>{item.label === 'Take a test' ? 'Test' : item.label === 'Explore directions' ? 'Explore' : item.label === 'Your progress' ? 'Progress' : 'Home'}</NavLink>)}</nav>
}

function StudentAppShell({ children, profile }: { children: React.ReactNode; profile: Profile }) {
  const location = useLocation()
  return <div className="app-shell student-shell"><StudentAppHeader profile={profile} /><div className="main-area"><main className="content"><AnimatePresence mode="wait"><motion.div key={location.pathname} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .25 }}>{children}</motion.div></AnimatePresence></main><footer className="site-footer"><span>IAQ / EXPERIMENTAL EDUCATIONAL PROFILE</span><span>Not a clinical diagnosis or officially normed IQ score.</span></footer></div><MobileStudentNavigation /></div>
}

function WorkspaceNavLink({ to, label, icon, active }: { to: string; label: string; icon: string; active: boolean }) {
  return <Link to={to} className={`workspace-nav-link ${active ? 'active' : ''}`}><span className="workspace-nav-icon">{icon}</span><span>{label}</span></Link>
}

function WorkspaceFrame({ children, profile, kind, groups }: { children: React.ReactNode; profile?: Profile; kind: 'counselor' | 'admin'; groups: { label?: string; items: { to: string; label: string; icon: string }[] }[] }) {
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  const isAdmin = kind === 'admin'
  const workspaceTitle = isAdmin ? 'IAQ Administration' : 'Counselor Workspace'
  const defaultHash = location.pathname === (isAdmin ? '/admin' : '/school') ? '#overview' : location.hash
  return <div className={`workspace-shell ${kind}-workspace`}><aside className={`workspace-sidebar ${mobileOpen ? 'is-open' : ''}`}><div className="workspace-sidebar-brand"><WorkspaceSwitcher active={workspaceTitle} /></div><div className="workspace-sidebar-label">{isAdmin ? 'Administration system' : 'Student support'}</div>{groups.map((group) => <div className="workspace-nav-group" key={group.label || 'primary'}>{group.label && <div className="workspace-group-label">{group.label}</div>}<nav aria-label={group.label || workspaceTitle}>{group.items.map((item) => <WorkspaceNavLink key={item.label} {...item} active={defaultHash === `#${item.to.split('#')[1] || 'overview'}`} />)}</nav></div>)}<div className="workspace-sidebar-bottom"><Link to="/methodology">Help & Methodology</Link><Link to="/privacy">Settings</Link></div></aside><div className="workspace-main"><header className="workspace-topbar"><button className="workspace-menu-toggle" onClick={() => setMobileOpen((value) => !value)} aria-label="Toggle workspace navigation">☰</button><div className="workspace-page-title"><span className="eyebrow">{workspaceTitle}</span><strong>{pageName(location.pathname)}</strong></div><div className="workspace-actions"><label className="workspace-search"><span>⌕</span><input aria-label="Search students" placeholder={isAdmin ? 'Search content' : 'Search students'} /></label>{isAdmin ? <Link to="/admin#item-bank" className="button primary workspace-action-button">Add item <span>＋</span></Link> : <Link to="/school#follow-ups" className="button secondary workspace-action-button">Invite student <span>＋</span></Link>}<ProfileMenu profile={profile} label={isAdmin ? 'Administrator' : 'Counselor'} /></div></header><main className="workspace-content"><AnimatePresence mode="wait"><motion.div key={location.pathname + location.hash} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .25 }}>{children}</motion.div></AnimatePresence></main><footer className="site-footer"><span>IAQ / {isAdmin ? 'ADMINISTRATION' : 'COUNSELOR WORKSPACE'}</span><span>Access is consent-aware and audit logged.</span></footer></div></div>
}

function CounselorAppShell({ children }: { children: React.ReactNode }) {
  return <WorkspaceFrame kind="counselor" groups={[{ items: [{ to: '/school#overview', label: 'Overview', icon: '⌂' }, { to: '/school#students', label: 'Students', icon: '♙' }, { to: '/school#cohorts', label: 'Cohorts', icon: '◌' }, { to: '/school#reports', label: 'Reports', icon: '▤' }, { to: '/school#follow-ups', label: 'Follow-ups', icon: '↗' }, { to: '/school#notes', label: 'Counselor Notes', icon: '✎' }] }]}>{children}</WorkspaceFrame>
}

function AdminAppShell({ children }: { children: React.ReactNode }) {
  return <WorkspaceFrame kind="admin" groups={[{ label: 'Content', items: [{ to: '/admin#overview', label: 'Overview', icon: '⌂' }, { to: '/admin#item-bank', label: 'Item Bank', icon: '▦' }, { to: '/admin#item-families', label: 'Item Families', icon: '◇' }, { to: '/admin#review-queue', label: 'Review Queue', icon: '↗' }, { to: '/admin#major-library', label: 'Major Library', icon: '✦' }] }, { label: 'Assessment system', items: [{ to: '/admin#assessments', label: 'Assessments', icon: '◈' }, { to: '/admin#forms', label: 'Forms', icon: '□' }, { to: '/admin#scoring', label: 'Scoring & Versions', icon: '⌁' }, { to: '/admin#item-health', label: 'Item Health', icon: '◒' }] }, { label: 'Operations', items: [{ to: '/admin#analytics', label: 'Analytics', icon: '◌' }, { to: '/admin#users', label: 'Users & Schools', icon: '♙' }, { to: '/admin#audit-logs', label: 'Audit Logs', icon: '≡' }, { to: '/admin#settings', label: 'Settings', icon: '⚙' }] }]}>{children}</WorkspaceFrame>
}

function PublicNavbar() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => {
    const update = () => setScrolled(window.scrollY > 16)
    window.addEventListener('scroll', update, { passive: true })
    return () => window.removeEventListener('scroll', update)
  }, [])
  const links = [{ to: '/welcome#how', label: 'How it works' }, { to: '/assess', label: 'Assessments' }, { to: '/compass', label: 'Explore directions' }, { to: '/welcome#schools', label: 'For schools' }, { to: '/methodology', label: 'Methodology' }]
  return <header className={`public-navbar ${scrolled ? 'scrolled' : ''}`}><div className="public-navbar-inner"><Brand to="/welcome" /><nav aria-label="Public navigation">{links.map((link) => <Link key={link.label} to={link.to}>{link.label}</Link>)}</nav><GlobalSearch compact /><button className="public-menu-toggle" onClick={() => setMobileOpen((value) => !value)} aria-expanded={mobileOpen}>Menu</button><div className="public-actions"><Link to="/auth/login" className="public-sign-in">Sign in</Link><ThemeToggle /><Link to="/assess" className="button primary magnetic">Take a test <span>→</span></Link></div></div>{mobileOpen && <nav className="public-mobile-menu" aria-label="Mobile public navigation">{links.map((link) => <Link key={link.label} to={link.to} onClick={() => setMobileOpen(false)}>{link.label}</Link>)}<Link to="/auth/login" onClick={() => setMobileOpen(false)}>Sign in</Link><GlobalSearch /></nav>}</header>
}

function PublicSite() {
  return <div className="public-site"><PublicNavbar /><main className="public-main"><section className="public-hero-grid"><div className="public-hero-copy"><div className="public-kicker">A clearer way to start thinking about what comes next</div><h1>See how you think.<br /><em>Then choose what to try.</em></h1><p>IAQ is a timed cognitive assessment for students who want useful evidence before exploring subjects, majors, and future directions.</p><div className="public-actions-large"><Link to="/assess" className="button primary">Start your assessment <span>→</span></Link><Link to="/methodology" className="text-button">How it works ↗</Link></div></div><aside className="public-hero-proof"><span className="eyebrow">The first release</span><strong>56</strong><span>questions across seven thinking areas</span><div className="public-proof-rule" /><div className="public-proof-meta"><span>35 min</span><span>private report</span><span>within-profile only</span></div></aside></section><section className="public-flow" id="how"><div className="public-flow-intro"><span className="eyebrow">A simple order</span><h2>Test first. Results next.</h2><p>Directions come after the evidence, so the next step has something real to build on.</p></div><div className="public-flow-steps"><article><b>01</b><h3>Take a test</h3><p>Answer 56 medium-to-hard questions in one focused, timed session.</p></article><article><b>02</b><h3>Read your report</h3><p>See seven domain scores, your average line, accuracy, and timing context.</p></article><article id="schools"><b>03</b><h3>Explore directions</h3><p>Use your profile and interests to choose small, practical things to try next.</p></article></div></section><section className="public-evidence"><div><span className="eyebrow">Built for honest progress</span><h2>One score is never the whole story.</h2></div><p>IAQ keeps results private and provisional. It is designed to support reflection and better conversations—not diagnosis, ranking, or a fixed label.</p><Link to="/methodology" className="text-button">Read the methodology ↗</Link></section></main></div>
}

function PageIntro({ eyebrow, title, body, action }: { eyebrow: string; title: React.ReactNode; body?: string; action?: React.ReactNode }) {
  return <div className="page-intro"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1>{body && <p className="lede">{body}</p>}</div>{action && <div className="intro-action">{action}</div>}</div>
}

function LegacyHome({ profile, savedMajors }: { profile: Profile; savedMajors: string[] }) {
  return <div className="page">
    <PageIntro eyebrow="Saturday, 05 September 2026 / 09:41" title={<>See how you think.<br /><em>Find what fits you.</em></>} body="Your profile brings together your thinking style, interests, and the things you have tried — so you can take a confident next step." action={<Link to="/results" className="button primary">See your potential <span>↗</span></Link>} />
    <div className="notice-bar"><span className="notice-icon">i</span><span><strong>Experimental profile.</strong> IAQ V1.0 results are educational and provisional. They are not a clinical diagnosis or an officially normed IQ score.</span><Link to="/methodology">Read methodology ↗</Link></div>
    <div className="dashboard-grid">
      <section className="panel profile-panel span-7"><div className="panel-top"><div><div className="eyebrow">Your thinking profile</div><h2>How your mind works today</h2></div><span className="mono-label">IAQ-COG-0.3</span></div><div className="profile-summary"><div className="composite"><span>Early snapshot</span><strong>{profile.composite || 74}<span>/100</span></strong><small>{profile.confidence || 'moderate'} confidence</small></div><div className="profile-chart"><ResponsiveContainer width="100%" height={190}><AreaChart data={domains.map((domain) => ({ name: domainMeta[domain].short, score: profile.scores[domain] }))} margin={{ left: 0, right: 0, top: 10, bottom: 0 }}><CartesianGrid vertical={false} stroke="#e1ded5" strokeDasharray="2 4" /><XAxis dataKey="name" tickLine={false} axisLine={false} tick={{ fill: '#777973', fontSize: 10 }} /><YAxis domain={[0, 100]} hide /><Tooltip contentStyle={{ border: '1px solid #d7d2c7', borderRadius: 0, boxShadow: 'none', fontSize: 12 }} /><Area type="monotone" dataKey="score" stroke="#315CFF" fill="#e5ebff" strokeWidth={2} /></AreaChart></ResponsiveContainer></div></div><div className="panel-footer"><span>What stands out: <b>{profile.strengths.join(' + ')}</b></span><Link to="/results">See the full picture ↗</Link></div></section>
      <section className="panel direction-panel span-5"><div className="panel-top"><div><div className="eyebrow">Find your path</div><h2>Ideas for your future</h2></div><span className="sparkle">✦</span></div><div className="direction-list">{majors.slice(0, 3).map((major, index) => <div className="direction-row" key={major.name}><span className="rank">0{index + 1}</span><div className="direction-name"><strong>{major.name}</strong><span>{major.family}</span></div><div className="mini-bar"><span style={{ width: `${major.fit}%`, background: major.accent }} /></div><span className="score-mono">{major.fit}</span></div>)}</div><div className="panel-footer"><span>{savedMajors.length ? `${savedMajors.length} saved idea${savedMajors.length > 1 ? 's' : ''}` : 'Save a path to revisit'}</span><Link to="/compass">Explore ideas ↗</Link></div></section>
      <section className="panel evidence-panel span-4"><div className="eyebrow">Your evidence / 03</div><h2>Add what you have tried</h2><p className="muted">The more real experiences you add, the more useful your profile becomes.</p><div className="evidence-stack"><EvidenceRow label="School subjects" value="3 added" state="good" /><EvidenceRow label="Projects & activities" value="2 added" state="good" /><EvidenceRow label="Your reflections" value="1 pending" state="pending" /></div><button className="text-button">Add an experience <span>＋</span></button></section>
      <section className="panel steps-panel span-8"><div className="panel-top"><div><div className="eyebrow">Your next moves / This month</div><h2>Try one small thing next.</h2></div><Link to="/tracker" className="text-button">Open my progress ↗</Link></div><div className="recommendation-grid">{recommendations.map((item) => <div className="recommendation" key={item.title}><span className="rec-icon">{item.icon}</span><span className="rec-label">{item.label}</span><h3>{item.title}</h3><p>{item.body}</p></div>)}</div></section>
    </div>
  </div>
}

function Home({ profile }: { profile: Profile; savedMajors: string[] }) {
  const hasResult = Boolean(profile.lastResult)
  const composite = profile.composite ?? null
  const ranked = [...domains].sort((a, b) => (profile.scores[b] ?? -1) - (profile.scores[a] ?? -1))
  return <div className="page home-page">
    <section className="compact-hero"><div><div className="eyebrow">IAQ / your starting point</div><h1>{hasResult ? <>Your result is ready.<br /><em>See what stands out.</em></> : <>Start with one test.<br /><em>See how you think.</em></>}</h1><p>{hasResult ? 'Read your private profile first. Explore directions only after you understand the evidence.' : 'A 35-minute assessment across seven thinking areas, followed by a clear visual report.'}</p></div><Link to={hasResult ? '/results' : '/assess'} className="button primary">{hasResult ? 'See my results' : 'Start test'} <span>→</span></Link></section>
    <div className="notice-bar compact-notice"><span className="notice-icon">i</span><span><strong>Private and provisional.</strong> This is an educational profile, not an official IQ score or diagnosis.</span><Link to="/methodology">How it works ↗</Link></div>
    <div className="dashboard-grid home-grid"><section className="panel home-result-preview span-8"><div className="panel-top"><div><div className="eyebrow">{hasResult ? 'Your results / seven areas' : 'Your result / seven areas'}</div><h2>{hasResult ? 'A clear picture of your thinking' : 'Your report will appear here'}</h2></div><span className="mono-label">{hasResult ? profile.lastAssessment : 'NOT STARTED'}</span></div><div className="home-result-body"><div className="home-score"><span>{hasResult ? 'IAQ profile score' : 'Complete the test'}</span><strong>{hasResult && composite !== null ? <AnimatedNumber value={composite} /> : '—'}{hasResult && composite !== null && <small>/100</small>}</strong><p>{hasResult ? `${profile.confidence || 'moderate'} confidence · within your profile` : 'Seven domain scores, accuracy, and timing context.'}</p></div><div className="home-bars" aria-label="Thinking profile preview">{ranked.map((domain) => <div className="home-bar-row" key={domain}><span>{domainMeta[domain].short}</span><i><b className={domainMeta[domain].tone} style={{ width: `${hasResult ? (profile.scores[domain] ?? 0) : 0}%` }} /></i><strong>{hasResult ? (profile.scores[domain] ?? '—') : '—'}</strong></div>)}</div></div><div className="panel-footer"><span>{hasResult ? `Strongest today: ${profile.strengths.join(' + ')}` : '56 questions · 35 minutes · randomized'}</span><Link to={hasResult ? '/results' : '/assess'}>{hasResult ? 'Read the full report ↗' : 'See the test details ↗'}</Link></div></section><aside className="panel home-start-panel span-4"><div className="eyebrow">The first step</div><div className="home-step-number">01</div><h2>{hasResult ? 'Now add context.' : 'Start the test.'}</h2><p>{hasResult ? 'Interests and real experiences are more useful after your result gives you a starting point.' : 'Answer carefully. The test chooses a balanced set from the question bank and submits when time runs out.'}</p><Link className="button secondary full" to={hasResult ? '/compass' : '/assess'}>{hasResult ? 'Explore directions' : 'Start test'} <span>→</span></Link></aside><section className="home-sequence span-12"><div><span className="eyebrow">A simple order</span><h2>Test first. Results next. Directions after.</h2></div><div className="sequence-steps"><Link to="/assess"><b>01</b><span>Take a test</span><small>35 minutes / 56 questions</small></Link><Link to="/results"><b>02</b><span>See your results</span><small>Seven visual domain scores</small></Link><Link to="/compass"><b>03</b><span>Explore directions</span><small>Use evidence, interests, and curiosity</small></Link></div></section></div>
  </div>
}

function EvidenceRow({ label, value, state }: { label: string; value: string; state: string }) { return <div className="evidence-row"><span className={`state-mark ${state}`}>{state === 'good' ? '✓' : '○'}</span><span>{label}</span><strong>{value}</strong></div> }

type DomainPreview = { task: string; detail: string; visual: 'abstract' | 'logic' | 'numbers' | 'verbal' | 'spatial' | 'memory' | 'speed' }

const domainPreviews: Record<Domain, DomainPreview> = {
  'Abstract reasoning': { task: 'Compare visual changes and infer the rule that connects them.', detail: 'Shapes may change position, count, direction, or fill across a grid.', visual: 'abstract' },
  'Deductive logic': { task: 'Read a set of conditions and choose the conclusion that must follow.', detail: 'The focus is on what the evidence guarantees—not what seems likely.', visual: 'logic' },
  'Numerical reasoning': { task: 'Trace relationships across sequences, ratios, and number structures.', detail: 'Look for the operation or relationship that stays consistent.', visual: 'numbers' },
  'Verbal reasoning': { task: 'Use meaning and evidence to assess an analogy, inference, or argument.', detail: 'The questions reward precise reading rather than specialist knowledge.', visual: 'verbal' },
  'Visual-spatial reasoning': { task: 'Mentally rotate, fold, and compare visual arrangements.', detail: 'You will work with position and form, not artistic drawing skill.', visual: 'spatial' },
  'Working memory': { task: 'Study a short sequence, then reorder or update it after it disappears.', detail: 'The task tests holding information briefly while following a rule.', visual: 'memory' },
  'Processing speed': { task: 'Compare symbols quickly while keeping exactness ahead of guessing.', detail: 'The timed setting captures both accuracy and the pace of your decisions.', visual: 'speed' }
}

function DomainPreviewVisual({ kind }: { kind: DomainPreview['visual'] }) {
  if (kind === 'abstract') return <svg viewBox="0 0 320 150" role="img" aria-label="Illustrative geometric rule preview"><g fill="none" stroke="currentColor" strokeWidth="2"><rect x="18" y="18" width="72" height="48" /><rect x="124" y="18" width="72" height="48" /><rect x="230" y="18" width="72" height="48" /><rect x="18" y="86" width="72" height="48" /><rect x="124" y="86" width="72" height="48" /><rect x="230" y="86" width="72" height="48" /></g><circle cx="54" cy="42" r="9" fill="currentColor" /><path d="M143 53 177 29M143 29l34 24" stroke="currentColor" strokeWidth="7" /><circle cx="266" cy="42" r="9" fill="none" /><path d="M36 122h36" stroke="currentColor" strokeWidth="7" /><circle cx="160" cy="110" r="9" fill="currentColor" /><path d="m252 125 27-27" stroke="currentColor" strokeWidth="7" /></svg>
  if (kind === 'logic') return <div className="preview-logic" aria-label="Illustrative conditions and conclusion preview"><div><span>If</span><strong>the archive is open</strong></div><div><span>and</span><strong>the blue file is inside</strong></div><div className="preview-conclusion"><span>then</span><strong>what must be true?</strong></div></div>
  if (kind === 'numbers') return <div className="preview-numbers" aria-label="Illustrative numerical relationship preview"><span>04</span><i>＋ 07</i><span>11</span><i>× 2</i><span>22</span><i>− 03</i><span>19</span></div>
  if (kind === 'verbal') return <div className="preview-verbal" aria-label="Illustrative reading and inference preview"><p>“The study group moved its meeting earlier. Attendance increased.”</p><div><span>Read for</span><strong>what the evidence supports</strong></div></div>
  if (kind === 'spatial') return <svg viewBox="0 0 320 150" role="img" aria-label="Illustrative rotation preview"><g fill="none" stroke="currentColor" strokeWidth="2"><rect x="24" y="37" width="76" height="76" /><rect x="220" y="37" width="76" height="76" /></g><path d="M59 91V60h31M260 60v31h-31" stroke="currentColor" strokeWidth="10" fill="none" /><path d="M134 75c13-22 39-22 52 0M180 75l6-12m-6 12 13-1" fill="none" stroke="currentColor" strokeWidth="3" /></svg>
  if (kind === 'memory') return <div className="preview-memory" aria-label="Illustrative working memory preview"><div><b>R</b><b>4</b><b>△</b><b>Q</b></div><span>Study briefly, then recall after the symbols disappear.</span></div>
  return <div className="preview-speed" aria-label="Illustrative exact symbol comparison preview"><div><span>Target</span><strong>◆ ○</strong></div><div><span>Compare</span><strong>◆ ○</strong></div><div><span>Exact?</span><b>YES</b></div></div>
}

function DomainExplorer() {
  const [selected, setSelected] = useState<Domain>('Abstract reasoning')
  const preview = domainPreviews[selected]
  const panelId = `domain-panel-${domainMeta[selected].short.toLowerCase()}`
  const selectFromKeyboard = (index: number, event: React.KeyboardEvent<HTMLButtonElement>) => {
    const direction = event.key === 'ArrowRight' || event.key === 'ArrowDown' ? 1 : event.key === 'ArrowLeft' || event.key === 'ArrowUp' ? -1 : 0
    if (!direction) return
    event.preventDefault()
    const next = domains[(index + direction + domains.length) % domains.length]
    setSelected(next)
    window.requestAnimationFrame(() => document.getElementById(`domain-tab-${domainMeta[next].short.toLowerCase()}`)?.focus())
  }
  return <section className="domain-explorer" aria-labelledby="domain-explorer-title"><div className="domain-explorer-head"><div><span className="eyebrow">What you will work through</span><h2 id="domain-explorer-title">Seven ways of thinking.</h2><p>Each area contributes eight questions to the same private profile.</p></div><span className="explorer-count">07 areas / 08 each</span></div><div className="domain-explorer-layout"><div className="domain-tabs" role="tablist" aria-label="Assessment domains">{domains.map((domain, index) => <button key={domain} id={`domain-tab-${domainMeta[domain].short.toLowerCase()}`} role="tab" type="button" aria-selected={selected === domain} aria-controls={`domain-panel-${domainMeta[domain].short.toLowerCase()}`} tabIndex={selected === domain ? 0 : -1} className={`domain-tab ${selected === domain ? 'active' : ''}`} onClick={() => setSelected(domain)} onKeyDown={(event) => selectFromKeyboard(index, event)}><span className="domain-tab-number">0{index + 1}</span><span><strong>{domain}</strong><small>{domainMeta[domain].description}</small></span><b aria-hidden="true">→</b></button>)}</div><div className={`domain-preview domain-preview-${domainMeta[selected].tone}`} role="tabpanel" id={panelId} aria-labelledby={`domain-tab-${domainMeta[selected].short.toLowerCase()}`}><div className="domain-preview-head"><span className="preview-label">Illustrative preview · not scored</span><span className="preview-domain">{selected}</span></div><h3>{preview.task}</h3><p>{preview.detail}</p><div className="domain-preview-visual"><DomainPreviewVisual kind={preview.visual} /></div><div className="domain-preview-foot"><span>One of seven areas</span><span>Results show patterns, not a verdict.</span></div></div></div><p className="domain-explorer-note"><span className="notice-icon">i</span> The assessment uses reviewed items selected from the question bank. These examples explain the task types; they are not live questions.</p></section>
}

function AssessLanding() {
  return <div className="page assess-page"><section className="assessment-prep-intro"><div><div className="eyebrow">IAQ / timed assessment</div><h1>Take a test.<br /><em>See how you think.</em></h1><p>One focused session. A clear visual report as soon as you finish.</p></div><Link to="/methodology" className="text-button prep-method-link">How the assessment works ↗</Link></section><div className="assessment-prep-grid"><DomainExplorer /><aside className="assessment-session-summary panel"><span className="eyebrow">Your session</span><h2>Ready when you are.</h2><p className="summary-lede">Find a quiet place and give yourself enough time to think carefully.</p><div className="session-facts"><div><strong>35</strong><span>minutes</span></div><div><strong>56</strong><span>questions</span></div><div><strong>8</strong><span>per area</span></div></div><div className="prep-guidance"><strong>Before you start</strong><p>The clock keeps running after a refresh or if you leave. Your place is saved, but time is not extended.</p><p>You can skip an item and return to it before submitting.</p></div><Link to="/assess/session" className="button primary full">Start test <span>→</span></Link><span className="session-footnote">Your result is private, provisional, and for within-profile reflection.</span></aside><section className="report-preview panel"><div><span className="eyebrow">After the test</span><h2>Your report puts the evidence first.</h2><p>See all seven domain scores sorted against your own average, with accuracy and timing context for each area.</p></div><div className="report-preview-bars" aria-label="Illustrative report bar chart"><span className="report-average-label">your average</span>{domains.map((domain, index) => <div key={domain}><span>{domainMeta[domain].short}</span><i><b className={domainMeta[domain].tone} style={{ width: `${[76, 62, 69, 57, 83, 65, 48][index]}%` }} /></i></div>)}</div><span className="report-preview-note">Illustrative shape only — no score is shown before you complete the assessment.</span></section></div></div>
}

function LegacyAssessment({ onComplete }: { onComplete: (scores: Record<Domain, number>) => void }) {
  const navigate = useNavigate()
  const [index, setIndex] = useState(0)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [paused, setPaused] = useState(false)
  const [startedAt] = useState(Date.now())
  const [apiSession, setApiSession] = useState<string | null>(null)
  const [apiQuestion, setApiQuestion] = useState<Question | null>(null)
  const [usingApi, setUsingApi] = useState(false)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [apiError, setApiError] = useState('')
  useEffect(() => {
    let alive = true
    startRandomizedAssessment().then(({ sessionId, question: first }) => {
      if (!alive) return
      setApiSession(sessionId)
      setApiQuestion(first)
      setUsingApi(true)
      setLoading(false)
    }).catch(() => {
      if (!alive) return
      setLoading(false)
    })
    return () => { alive = false }
  }, [])
  const question = usingApi && apiQuestion ? apiQuestion : questions[index]
  const selected = answers[question.id]
  const answered = Object.keys(answers).length
  const totalQuestions = usingApi ? 56 : questions.length
  const progress = Math.round((answered / totalQuestions) * 100)
  const choose = (option: string) => setAnswers((current) => ({ ...current, [question.id]: option }))
  const next = async () => {
    if (!selected || submitting) return
    if (usingApi && apiSession) {
      setSubmitting(true)
      setApiError('')
      try {
        const nextQuestion = await saveAndGetNext(apiSession, question, selected, answered + 1, 10000)
        setAnswers((current) => ({ ...current, [question.id]: selected }))
        if (nextQuestion) setApiQuestion(nextQuestion)
        else {
          await finishAssessment(apiSession)
          onComplete(initialScores)
          navigate('/results')
        }
      } catch {
        setApiError('We could not save this answer. Check the connection and try again.')
      } finally {
        setSubmitting(false)
      }
    } else if (index === questions.length - 1) {
      onComplete(initialScores)
      navigate('/results')
    } else setIndex((i) => i + 1)
  }
  const restart = async () => {
    setIndex(0)
    setAnswers({})
    setPaused(false)
    setApiError('')
    if (usingApi) {
      setLoading(true)
      try {
        const { sessionId, question: first } = await startRandomizedAssessment()
        setApiSession(sessionId)
        setApiQuestion(first)
      } catch {
        setUsingApi(false)
      } finally {
        setLoading(false)
      }
    }
  }
  if (loading) return <div className="assessment-screen"><main className="assessment-main"><div className="loading-card"><div className="eyebrow">Preparing your test</div><h1>Picking a fresh set of questions…</h1><p>We are choosing a balanced mix from the IAQ question bank.</p></div></main></div>
  const displayNumber = usingApi ? (answers[question.id] ? answered : answered + 1) : index + 1
  return <div className="assessment-screen"><header className="assessment-header"><div className="assessment-brand"><Brand /><span className="assessment-name">IAQ Cognitive Profile</span></div><div className="assessment-progress"><span>Assessment progress</span><div className="progress-track"><span style={{ width: `${Math.max(5, progress)}%` }} /></div><span className="mono-label">{String(Math.min(displayNumber, totalQuestions)).padStart(2, '0')} / {totalQuestions}</span></div><div className="assessment-actions"><button className="text-button" onClick={() => setPaused(true)}>Pause</button><button className="text-button" onClick={() => setApiError('Technical issue noted. If this continues, exit and restart the assessment.')}>Report issue</button><Link className="assessment-exit" to="/">Exit assessment</Link></div></header><main className="assessment-main"><div className="assessment-meta"><span className="eyebrow">Question {String(Math.min(displayNumber, totalQuestions)).padStart(2, '0')} / {question.domain}</span><span className="timer-label">◷ {Math.max(1, Math.floor((Date.now() - startedAt) / 60000))} min</span></div><AnimatePresence mode="wait"><motion.div key={question.id} className="question-card" initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -18 }} transition={{ duration: .2 }}><div className="question-copy"><h1>{question.prompt}</h1>{question.helper && <p>{question.helper}</p>}</div>{(question.visual || question.renderType === 'svg_stimulus') && <DeterministicStimulus question={question} />}<div className="option-grid">{question.options.map((option, optionIndex) => <button key={option} className={`option ${selected === option ? 'selected' : ''}`} onClick={() => choose(option)}><span className="option-letter">{String.fromCharCode(65 + optionIndex)}</span><span>{option}</span><span className="option-check">{selected === option ? '✓' : ''}</span></button>)}</div></motion.div></AnimatePresence><div className="assessment-controls"><button className="button ghost" disabled={usingApi || index === 0} onClick={() => setIndex((i) => Math.max(0, i - 1))}>← Previous</button><span className="autosave">{selected ? (usingApi ? 'Ready to save' : 'Answer saved locally') : 'Select one answer to continue'}</span><button className="button primary" disabled={!selected || submitting} onClick={next}>{submitting ? 'Saving…' : displayNumber === totalQuestions ? 'See profile' : 'Continue'} <span>→</span></button></div>{apiError && <div className="assessment-inline-error">{apiError}</div>}<div className="assessment-footnote">{usingApi ? '56 questions / 8 from each thinking area / randomized for this attempt.' : 'Demo fallback / 14 questions / start the IAQ API for a randomized 56-question form.'}</div></main>{paused && <div className="modal-backdrop"><div className="modal"><button className="modal-close" onClick={() => setPaused(false)} aria-label="Close">×</button><div className="eyebrow">Session saved</div><h2>Your progress is safe.</h2><p>You have answered {answered} of {totalQuestions} questions. Resume when you have a quiet moment.</p><div className="modal-actions"><button className="button ghost" onClick={() => setPaused(false)}>Keep going</button><button className="button primary" onClick={() => { setPaused(false); navigate('/') }}>Exit assessment</button></div><button className="text-button" onClick={restart}>Restart this test</button></div></div>}</div>
}

function DeterministicStimulus({ question }: { question: Question }) {
  const seed = `${question.id}:${String(question.renderParameters?.seed || '')}`
  const hash = [...seed].reduce((total, character) => total + character.charCodeAt(0), 0)
  const shapes = ['circle', 'square', 'triangle', 'diamond']
  const fills = ['outline', 'solid', 'striped']
  const tiles = question.visual?.length ? question.visual : [0, 1, 2].map((offset) => `${shapes[(hash + offset) % shapes.length]}:${fills[(hash + offset * 2) % fills.length]}:${((hash + offset) * 90) % 360}`)
  const drawShape = (shape: string, fill: string, rotation: number) => {
    const paint = fill === 'solid' ? '#0B1220' : 'none'
    const stroke = '#315CFF'
    const patternId = `stripe-${question.id.replace(/[^a-z0-9]/gi, '')}`
    if (shape === 'circle') return <circle cx="50" cy="50" r="26" fill={paint} stroke={stroke} strokeWidth="4" />
    const points = shape === 'triangle' ? '50,18 80,78 20,78' : shape === 'diamond' ? '50,15 82,50 50,85 18,50' : '22,22 78,22 78,78 22,78'
    return <polygon points={points} fill={fill === 'striped' ? `url(#${patternId})` : paint} stroke={stroke} strokeWidth="4" transform={`rotate(${rotation} 50 50)`} />
  }
  return <div className="stimulus" aria-label="Visual stimulus generated from a deterministic item rule"><div className="stimulus-svg-row">{tiles.map((tile, index) => {
    const [shape, fill, rotationText] = tile.includes(':') ? tile.split(':') : [shapes[(hash + index) % shapes.length], fills[(hash + index) % fills.length], String((hash + index) * 90 % 360)]
    const rotation = Number(rotationText) || 0
    return <svg className="stimulus-tile" viewBox="0 0 100 100" role="img" aria-label={`${fill} ${shape} visual ${index + 1}`} key={`${tile}-${index}`}><defs><pattern id={`stripe-${question.id.replace(/[^a-z0-9]/gi, '')}`} width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="8" stroke="#315CFF" strokeWidth="3" /></pattern></defs>{drawShape(shape, fill, rotation)}</svg>
  })}</div><span className="stimulus-note">deterministic visual stimulus</span></div>
}

function Assessment({ onComplete }: { onComplete: (result: AssessmentResult) => void }) {
  const navigate = useNavigate()
  const submissionStarted = useRef(false)
  const [apiSession, setApiSession] = useState<string | null>(null)
  const [question, setQuestion] = useState<Question | null>(null)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [questionStartedAt, setQuestionStartedAt] = useState(Date.now())
  const [answeredBaseline, setAnsweredBaseline] = useState(0)
  const [deadlineAt, setDeadlineAt] = useState<string | null>(null)
  const [timeLeft, setTimeLeft] = useState(2100)
  const [totalQuestions, setTotalQuestions] = useState(56)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [apiError, setApiError] = useState('')

  const begin = async () => {
    setLoading(true)
    setApiError('')
    try {
      const savedSessionId = window.sessionStorage.getItem(ASSESSMENT_SESSION_KEY)
      let started
      if (savedSessionId) {
        try {
          started = await resumeRandomizedAssessment(savedSessionId)
        } catch {
          // A browser can retain a session after a local API restart. That stale
          // pointer must not prevent a student from starting a new assessment.
          window.sessionStorage.removeItem(ASSESSMENT_SESSION_KEY)
          started = await startRandomizedAssessment()
        }
      } else {
        started = await startRandomizedAssessment()
      }
      window.sessionStorage.setItem(ASSESSMENT_SESSION_KEY, started.sessionId)
      setApiSession(started.sessionId)
      setQuestion(started.question)
      setDeadlineAt(started.deadlineAt)
      setTimeLeft(Math.max(0, Math.ceil((new Date(started.deadlineAt).getTime() - Date.now()) / 1000)))
      setTotalQuestions(started.questionCount)
      setAnsweredBaseline(started.answeredCount)
      setQuestionStartedAt(Date.now())
    } catch (error) {
      setApiError(error instanceof Error ? error.message : 'We could not prepare the test.')
    } finally {
      setLoading(false)
    }
  }

  const finalize = async () => {
    if (!apiSession || submissionStarted.current) return
    submissionStarted.current = true
    setSubmitting(true)
    try {
      const result = await finishAssessment(apiSession)
      window.sessionStorage.removeItem(ASSESSMENT_SESSION_KEY)
      onComplete(result)
      navigate('/results')
    } catch (error) {
      submissionStarted.current = false
      setApiError(error instanceof Error ? error.message : 'We could not create your result.')
      setSubmitting(false)
    }
  }

  useEffect(() => { void begin() }, [])
  useEffect(() => {
    if (!deadlineAt) return
    const tick = () => setTimeLeft(Math.max(0, Math.ceil((new Date(deadlineAt).getTime() - Date.now()) / 1000)))
    tick()
    const timer = window.setInterval(tick, 1000)
    return () => window.clearInterval(timer)
  }, [deadlineAt])
  useEffect(() => { if (timeLeft === 0 && apiSession) void finalize() }, [timeLeft, apiSession])

  const selected = question ? answers[question.id] : undefined
  const currentSelection = selected ? 1 : 0
  const answered = Math.max(0, answeredBaseline + Object.keys(answers).length - currentSelection)
  const progress = Math.round(((answered + currentSelection) / totalQuestions) * 100)
  const choose = (option: string) => { if (!submitting && question) setAnswers((current) => ({ ...current, [question.id]: option })) }
  const next = async () => {
    if (!question || !selected || !apiSession || submitting || timeLeft === 0) return
    setSubmitting(true)
    setApiError('')
    try {
      const nextQuestion = await saveAndGetNext(apiSession, question, selected, answered + 1, Math.max(0, Date.now() - questionStartedAt))
      setAnswers((current) => ({ ...current, [question.id]: selected }))
      if (nextQuestion) {
        setQuestion(nextQuestion)
        setQuestionStartedAt(Date.now())
        setSubmitting(false)
      } else {
        await finalize()
      }
    } catch (error) {
      setApiError(error instanceof Error ? error.message : 'We could not save this answer. Check your connection and try again.')
      setSubmitting(false)
    }
  }

  if (loading) return <div className="assessment-screen"><main className="assessment-main"><div className="loading-card"><div className="eyebrow">Preparing your test</div><h1>Picking a fresh set of questions…</h1><p>We are choosing eight questions from each thinking area.</p></div></main></div>
  if (!question) return <div className="assessment-screen"><main className="assessment-main"><div className="loading-card error-card"><div className="eyebrow">The test is not ready</div><h1>We could not start your test.</h1><p>{apiError || 'Start the IAQ API, then try again.'}</p><button className="button primary" onClick={() => { submissionStarted.current = false; void begin() }}>Try again <span>↻</span></button></div></main></div>

  const minutes = Math.floor(timeLeft / 60).toString().padStart(2, '0')
  const seconds = (timeLeft % 60).toString().padStart(2, '0')
  const timerClass = timeLeft <= 300 ? 'timer-warning' : timeLeft <= 600 ? 'timer-caution' : ''
  return <div className="assessment-screen"><header className="assessment-header"><div className="assessment-brand"><Brand /><span className="assessment-name">IAQ Cognitive Profile</span></div><div className="assessment-progress"><span>Progress</span><div className="progress-track"><span style={{ width: `${Math.max(3, progress)}%` }} /></div><span className="mono-label">{String(Math.min(answered + 1, totalQuestions)).padStart(2, '0')} / {totalQuestions}</span></div><div className="assessment-actions"><button className="text-button" onClick={() => setApiError('Your test is timed. If you leave, the countdown continues.')}>Need help?</button><Link className="assessment-exit" to="/">Leave test</Link></div></header><main className="assessment-main"><div className="assessment-meta"><span className="eyebrow">Question {String(Math.min(answered + 1, totalQuestions)).padStart(2, '0')} / {question.domain}</span><span className={`timer-label ${timerClass}`} aria-live="polite">Time left {minutes}:{seconds}</span></div>{timeLeft <= 600 && <div className={`timer-notice ${timerClass}`}>{timeLeft <= 300 ? 'Five minutes left. Choose your best answer and keep moving.' : 'Ten minutes left. Keep an eye on the clock.'}</div>}<AnimatePresence mode="wait"><motion.div key={question.id} className="question-card" initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -18 }} transition={{ duration: .2 }}><div className="question-copy"><h1>{question.prompt}</h1>{question.helper && <p>{question.helper}</p>}</div>{(question.visual || question.renderType === 'svg_stimulus') && <DeterministicStimulus question={question} />}<div className="option-grid">{question.options.map((option, optionIndex) => <button key={option} className={`option ${selected === option ? 'selected' : ''}`} onClick={() => choose(option)} aria-pressed={selected === option}><span className="option-letter">{String.fromCharCode(65 + optionIndex)}</span><span>{option}</span><span className="option-check">{selected === option ? '✓' : ''}</span></button>)}</div></motion.div></AnimatePresence><div className="assessment-controls"><span className="autosave">{selected ? 'Answer ready' : 'Choose one answer to continue'}</span><button className="button primary" disabled={!selected || submitting || timeLeft === 0} onClick={next}>{submitting ? 'Saving…' : answered + 1 >= totalQuestions ? 'See my results' : 'Next question'} <span>→</span></button></div>{apiError && <div className="assessment-inline-error" role="alert">{apiError}</div>}<div className="assessment-footnote">35 minutes total · 8 questions from each thinking area · your answers are saved as you go.</div></main></div>
}

function Compass({ profile, savedMajors, toggleMajor }: { profile: Profile; savedMajors: string[]; toggleMajor: (name: string) => void }) {
  const [filter, setFilter] = useState('All directions')
  const [aiConfigured, setAiConfigured] = useState<boolean | null>(null)
  const [aiDirections, setAiDirections] = useState<AIDirectionContext[]>([])
  const [aiBusy, setAiBusy] = useState(false)
  const [aiMessage, setAiMessage] = useState('')
  const [interestResult, setInterestResult] = useState<InterestResult | null>(null)
  useEffect(() => { void getAIStatus().then((status) => setAiConfigured(status.enabled)).catch(() => setAiConfigured(false)) }, [])
  useEffect(() => { void getInterestResult().then((result) => setInterestResult(result)).catch(() => undefined) }, [])
  const filters = ['All directions', 'Technology', 'Design', 'People & behaviour']
  const shown = filter === 'All directions' ? majors : majors.filter((major) => major.family.toLowerCase().includes(filter.split(' ')[0].toLowerCase()))
  const interestCode = interestResult?.code || '—'
  const interestScores = ['R', 'I', 'A', 'S', 'E', 'C'].map((code) => interestResult?.scores?.[code] ?? 0)
  const generateAI = async () => { if (!profile.lastResult) { setAiMessage('Complete the assessment first so the direction assistant has real evidence.'); return }; setAiBusy(true); setAiMessage(''); try { const response = await requestAIDirections(profile.lastResult.id); setAiDirections(response.directions) } catch (error) { setAiMessage(error instanceof Error ? error.message : 'AI direction context is not available yet.') } finally { setAiBusy(false) } }
  return <div className="page"><PageIntro eyebrow="Find your path / Explore ideas" title={<>Explore what could<br /><em>fit you.</em></>} body="Tell us what you enjoy, then compare possible paths by fit, readiness, and what you could try next." action={<button className="button primary" onClick={() => document.getElementById('questionnaire')?.scrollIntoView({ behavior: 'smooth' })}>Tell us what you like <span>↓</span></button>} /><div className="compass-summary"><div><span className="eyebrow">Your interest code</span><div className="riasec-code">{interestCode}</div><p>{interestResult?.status === 'not_started' ? 'Complete the interest check-in to see your code.' : 'Exploratory context, not a fixed label.'}</p></div><div className="compass-summary-copy"><strong>{interestResult ? 'Your interests add useful context.' : 'Start with the evidence.'}</strong><span>Interests can change. Use this page to compare ideas and choose a small next experiment.</span></div><div className="riasec-mini">{['R', 'I', 'A', 'S', 'E', 'C'].map((code, i) => <div key={code}><span>{code}</span><i style={{ height: `${interestScores[i]}%` }} /></div>)}</div></div><section className="major-explorer"><div className="explorer-head"><div><div className="eyebrow">Five ideas / explained simply</div><h2>What sounds interesting?</h2></div><div className="filter-row">{filters.map((item) => <button key={item} className={filter === item ? 'filter active' : 'filter'} onClick={() => setFilter(item)}>{item}</button>)}</div></div><div className="major-grid">{shown.map((major) => <MajorCard key={major.name} major={major} saved={savedMajors.includes(major.name)} onSave={() => toggleMajor(major.name)} />)}</div></section><section className="panel ai-directions-panel"><div className="panel-top"><div><div className="eyebrow">Optional AI context</div><h2>Ask for practical next ideas.</h2></div><span className="mono-label">AI_ASSISTED</span></div><p className="muted">The deterministic matches stay the source of truth. AI can explain why a direction may be worth exploring and suggest a small experiment, but it cannot predict your future.</p>{aiConfigured === false && <p className="ai-status">AI is not active. Add <code>OPENAI_API_KEY</code> to the backend server environment, then restart the API.</p>}{aiConfigured !== false && <button className="button secondary" onClick={generateAI} disabled={aiBusy || !profile.lastResult}>{aiBusy ? 'Thinking through the evidence…' : profile.lastResult ? 'Generate direction ideas' : 'Complete the test first'} <span>→</span></button>}{aiMessage && <p className="ai-status" role="status">{aiMessage}</p>}{aiDirections.length > 0 && <div className="ai-direction-list">{aiDirections.map((direction) => <article key={direction.slug}><div><span className="eyebrow">{direction.name}</span><h3>Why explore this</h3><p>{direction.why_this_may_fit}</p></div><div><h3>Try next</h3><p>{direction.try_next}</p></div><small>{direction.caution}</small></article>)}</div>}</section><section className="questionnaire" id="questionnaire"><div><div className="eyebrow">One quick question</div><h2>Make your profile more you.</h2><p>Interests can change. Tell us what you enjoy doing, not what you think you should choose.</p></div><div className="question-card compact"><span className="eyebrow">When you have a free afternoon, what sounds most satisfying?</span><div className="questionnaire-options">{['Make something visual', 'Solve a puzzling problem', 'Help someone untangle a problem', 'Organise an idea or plan'].map((item, i) => <button key={item} onClick={(e) => { (e.currentTarget as HTMLButtonElement).classList.toggle('selected') }}><span>{String.fromCharCode(65 + i)}</span>{item}</button>)}</div><button className="button primary small">Save my answer <span>→</span></button></div></section></div>
}

function MajorCard({ major, saved, onSave }: { major: Major; saved: boolean; onSave: () => void }) { return <article className="major-card" style={{ '--accent': major.accent } as React.CSSProperties}><div className="major-card-accent" /><div className="major-head"><div><span className="eyebrow">{major.family}</span><h3>{major.name}</h3></div><button className={`save-button ${saved ? 'saved' : ''}`} onClick={onSave} aria-label={saved ? `Remove ${major.name}` : `Save ${major.name}`}>{saved ? '★' : '☆'}</button></div><p>{major.reason}</p><div className="major-metrics"><Metric label="Fit" value={major.fit} /><Metric label="Ready now" value={major.readiness} /><Metric label="Confidence" value={major.confidence} /></div><div className="major-card-foot"><span className={`feasibility ${major.feasibility.toLowerCase().replaceAll(' ', '-')}`}>{major.feasibility}</span><button className="text-button">Explore ↗</button></div></article> }
function Metric({ label, value }: { label: string; value: number }) { return <div className="metric"><span>{label}</span><strong>{value}</strong><div className="metric-bar"><i style={{ width: `${value}%` }} /></div></div> }

function LegacyResults({ profile, savedMajors, toggleMajor }: { profile: Profile; savedMajors: string[]; toggleMajor: (name: string) => void }) {
  const chartData = domains.map((domain) => ({ subject: domainMeta[domain].short, score: profile.scores[domain] }))
  const fitData = majors.map((major) => ({ x: major.fit, y: major.readiness, name: major.name, fill: major.accent }))
  return <div className="page"><PageIntro eyebrow="See your potential / Your report" title={<>See your potential.<br /><em>Keep exploring.</em></>} body="Here is a simple snapshot of how you think, what interests you, and what you could try next." action={<button className="button primary" onClick={() => window.print()}>Print my report <span>↗</span></button>} /><div className="result-disclaimer"><div className="disclaimer-mark">!</div><div><strong>Experimental IAQ Composite / 74</strong><p>This V1.0 result is an experimental educational profile, not a clinical diagnosis or officially normed IQ score. It should support reflection and conversation.</p></div><Link to="/methodology">Why this matters ↗</Link></div><div className="result-grid"><section className="panel cognitive-panel span-7"><div className="panel-top"><div><div className="eyebrow">Your thinking snapshot / 07 areas</div><h2>How you think today</h2></div><span className="confidence-badge">Moderate confidence</span></div><div className="domain-bars">{domains.map((domain) => <div className="result-domain" key={domain}><div className="result-domain-label"><span>{domain}</span><b>{profile.scores[domain]}</b></div><div className="result-bar"><i className={domainMeta[domain].tone} style={{ width: `${profile.scores[domain]}%` }} /><span style={{ left: `${profile.scores[domain]}%` }} /></div><p>{domainMeta[domain].description}</p></div>)}</div><div className="result-caption"><span><i className="legend-dot cobalt" /> your profile today</span><span><i className="legend-line" /> no population percentile shown</span></div></section><section className="panel chart-panel span-5"><div className="eyebrow">A quick look</div><h2>Your strengths, side by side</h2><p className="muted">Spatial and abstract tasks stand out today. Speed is a developing signal — it deserves context, not a fixed label.</p><div className="radar-like"><ResponsiveContainer width="100%" height={230}><AreaChart data={chartData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}><CartesianGrid stroke="#e5e1d8" vertical={false} /><XAxis dataKey="subject" tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: '#72746e' }} /><YAxis domain={[0, 100]} tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: '#9c9b93' }} /><Area type="monotone" dataKey="score" stroke="#315CFF" fill="#315CFF" fillOpacity={.1} strokeWidth={2} /><ReferenceLine y={74} stroke="#1AAE91" strokeDasharray="4 4" /></AreaChart></ResponsiveContainer></div><Link to="/tracker" className="text-button">See my progress ↗</Link></section><section className="panel interest-panel span-5"><div className="eyebrow">What interests you</div><div className="interest-head"><h2>I · A · C</h2><span>top three</span></div><p><strong>You like ideas that make sense.</strong> You may enjoy understanding how things work, making ideas visible, and bringing structure to open-ended problems.</p><div className="interest-bars">{['Investigative', 'Artistic', 'Conventional', 'Realistic', 'Social', 'Enterprising'].map((item, i) => <div key={item}><span>{item}</span><i><b style={{ width: `${[92, 78, 65, 42, 35, 28][i]}%` }} /></i></div>)}</div><span className="muted tiny">Your interests can change as you try real things.</span></section><section className="panel fit-panel span-7"><div className="panel-top"><div><div className="eyebrow">Paths you could explore</div><h2>What might fit you?</h2></div><span className="mono-label">5 ideas / 3 alternatives</span></div><p className="muted">Fit is how well a path matches your profile. Readiness is what you have evidence for today. Neither is a permanent limit.</p><div className="fit-chart"><ResponsiveContainer width="100%" height={250}><ScatterChart margin={{ top: 20, right: 30, bottom: 20, left: -12 }}><CartesianGrid stroke="#e3dfd5" /><XAxis type="number" dataKey="x" domain={[50, 100]} tick={{ fontSize: 10 }} tickLine={false} axisLine={false} label={{ value: 'Fit →', position: 'insideBottom', offset: -10, fontSize: 10 }} /><YAxis type="number" dataKey="y" domain={[45, 100]} tick={{ fontSize: 10 }} tickLine={false} axisLine={false} label={{ value: 'Ready now', angle: -90, position: 'insideLeft', fontSize: 10 }} /><Tooltip cursor={{ strokeDasharray: '3 3' }} content={({ active, payload }) => active && payload?.[0] ? <div className="scatter-tooltip">{payload[0].payload.name}<strong>{payload[0].payload.x} fit · {payload[0].payload.y} ready</strong></div> : null} /><Scatter data={fitData} shape={(props: any) => <circle cx={props.cx} cy={props.cy} r={7} fill={props.payload.fill} stroke="#fff" strokeWidth={2} />} /></ScatterChart></ResponsiveContainer></div><div className="quadrant-legend"><span><i className="dot teal" /> ready to try</span><span><i className="dot coral" /> build evidence</span><span><i className="dot ink" /> prepare first</span></div></section><section className="panel plan-panel span-12"><div className="panel-top"><div><div className="eyebrow">Your next four weeks</div><h2>Try something small next.</h2></div><span className="plan-number">04</span></div><div className="plan-grid">{[{ week: '01', title: 'Compare courses', body: 'Look at two Computer Science degree plans. Notice which subjects make you curious.', status: 'This week' }, { week: '02', title: 'Make a tiny project', body: 'Build a small data story or interactive page. Keep it rough and learn from it.', status: 'Next' }, { week: '03', title: 'Talk to a person', body: 'Ask a CS student or professional what their normal week really looks like.', status: 'Later' }, { week: '04', title: 'Write what you noticed', body: 'What gave you energy? What felt hard in a useful way? Add it to My progress.', status: 'Later' }].map((item) => <div className="plan-item" key={item.week}><span className="week-no">{item.week}</span><div><span className="rec-label">{item.status}</span><h3>{item.title}</h3><p>{item.body}</p></div><span className="plan-check">○</span></div>)}</div></section></div></div>
}

function ReportDeliveryCard({ resultId }: { resultId?: string }) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [age, setAge] = useState('')
  const [granted, setGranted] = useState(false)
  const [status, setStatus] = useState('')
  const [submitting, setSubmitting] = useState(false)
  if (!resultId) return null
  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setSubmitting(true)
    setStatus('')
    try {
      await requestReportDelivery(resultId, { name, email, age: age ? Number(age) : undefined, guardian_consent_id: localStorage.getItem('iaq-guardian-consent-id') || undefined, granted })
      setStatus('Your report is queued. In production it will arrive from the IAQ report service.')
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'We could not queue the report.')
    } finally {
      setSubmitting(false)
    }
  }
  return <section className="panel report-delivery-card"><div><div className="eyebrow">Keep a private copy</div><h2>Send me my report.</h2><p>Results stay on this page immediately. Add your details only if you want a copy sent by email.</p></div><form onSubmit={submit} className="report-delivery-form"><label>Name<input value={name} onChange={(event) => setName(event.target.value)} required placeholder="Your name" /></label><label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required placeholder="you@example.com" /></label><label>Age <span className="field-note">(used for consent rules)</span><input type="number" min="13" max="120" value={age} onChange={(event) => setAge(event.target.value)} placeholder="Optional" /></label><label className="consent-check"><input type="checkbox" checked={granted} onChange={(event) => setGranted(event.target.checked)} required /> I agree to receive this private report by email.</label><button className="button primary" disabled={submitting}>{submitting ? 'Queuing…' : 'Send my report'} <span>→</span></button>{status && <p className="report-status" role="status">{status}</p>}</form></section>
}

function AIInterpretationCard({ resultId }: { resultId: string }) {
  const [status, setStatus] = useState<'idle' | 'loading' | 'ready' | 'unavailable'>('idle')
  const [message, setMessage] = useState('')
  const [interpretation, setInterpretation] = useState<AIInterpretation | null>(null)
  const generate = async () => {
    setStatus('loading')
    setMessage('')
    try { setInterpretation(await requestAIInterpretation(resultId)); setStatus('ready') }
    catch (error) { setStatus('unavailable'); setMessage(error instanceof Error ? error.message : 'AI interpretation is not available yet.') }
  }
  return <section className="panel ai-insight-card"><div className="panel-top"><div><div className="eyebrow">Optional AI reading</div><h2>Put the result into plain language.</h2></div><span className="mono-label">AI_ASSISTED / NOT SCORING</span></div><p className="muted">The score already comes from IAQ’s deterministic scorer. This optional layer only explains the evidence and suggests a careful next step.</p>{status === 'ready' && interpretation ? <div className="ai-insight-grid"><div><strong>What stands out</strong>{interpretation.narrative.what_stands_out.map((item) => <p key={item}>• {item}</p>)}</div><div><strong>Where to look for more evidence</strong>{interpretation.narrative.where_more_evidence.map((item) => <p key={item}>• {item}</p>)}</div><div><strong>Timing context</strong><p>{interpretation.narrative.timing_context}</p></div><div><strong>One next step</strong><p>{interpretation.narrative.next_step}</p></div></div> : <button className="button secondary" onClick={generate} disabled={status === 'loading'}>{status === 'loading' ? 'Preparing a careful read…' : 'Generate my plain-language read'} <span>→</span></button>}{status === 'unavailable' && <p className="ai-status" role="status">{message}</p>}<small className="ai-boundary">AI output is advisory, provisional, and never changes your score.</small></section>
}

function IdentityCaptureCard({ onComplete }: { onComplete: () => void }) {
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [ageBand, setAgeBand] = useState<'15-17' | '18-22' | 'adult' | 'unknown'>('18-22')
  const [guardianEmail, setGuardianEmail] = useState('')
  const [granted, setGranted] = useState(false)
  const [status, setStatus] = useState('')
  const [saving, setSaving] = useState(false)
  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setSaving(true)
    setStatus('')
    try {
      const identity = await captureIdentity({ email, display_name: displayName, age_band: ageBand, guardian_email: ageBand === '15-17' ? guardianEmail : undefined, granted })
      if (identity.guardian_consent?.id) localStorage.setItem('iaq-guardian-consent-id', identity.guardian_consent.id)
      localStorage.setItem('iaq-identity-captured', 'true')
      onComplete()
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'We could not save your details yet.')
    } finally {
      setSaving(false)
    }
  }
  return <section className="panel identity-capture-card"><div className="eyebrow">One last step before your score</div><h2>Tell us where to send your private report.</h2><p>We use your name, email, age band, and consent to protect the pilot record. Your result stays private and is not a public score card.</p><form onSubmit={submit} className="report-delivery-form"><label>Name<input value={displayName} onChange={(event) => setDisplayName(event.target.value)} required placeholder="Your name" /></label><label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required placeholder="you@example.com" /></label><label>Age band<select value={ageBand} onChange={(event) => setAgeBand(event.target.value as typeof ageBand)}><option value="15-17">15–17</option><option value="18-22">18–22</option><option value="adult">23+</option><option value="unknown">Prefer not to say</option></select></label>{ageBand === '15-17' && <label>Guardian email<input type="email" value={guardianEmail} onChange={(event) => setGuardianEmail(event.target.value)} required placeholder="guardian@example.com" /><span className="field-note">A guardian must approve the pilot record before a full report can be delivered.</span></label>}<label className="consent-check"><input type="checkbox" checked={granted} onChange={(event) => setGranted(event.target.checked)} required /> I agree to the IAQ pilot data notice and private report rules.</label><button className="button primary" disabled={saving}>{saving ? 'Saving…' : 'Continue to my result'} <span>→</span></button>{status && <p className="report-status" role="alert">{status}</p>}</form></section>
}

function Results({ profile }: { profile: Profile; savedMajors: string[]; toggleMajor: (name: string) => void }) {
  const result = profile.lastResult
  const [identityRequired, setIdentityRequired] = useState(() => localStorage.getItem('iaq-identity-captured') !== 'true')
  if (!result) return <div className="page results-empty"><PageIntro eyebrow="Your results / Private report" title={<>Your report starts<br /><em>after your test.</em></>} body="Complete the 35-minute assessment to see your actual answers, timing, and seven-domain profile." action={<Link className="button primary" to="/assess">Start test <span>→</span></Link>} /><section className="panel empty-report-panel"><div className="eyebrow">No scored result yet</div><h2>Nothing to compare yet.</h2><p>IAQ will never fill this report with a demo score. Your bars appear after a real session is submitted.</p><Link className="text-button" to="/methodology">Read how scoring works ↗</Link></section></div>
  if (identityRequired) return <div className="page results-page"><PageIntro eyebrow="Your results / Private report" title={<>Your test is done.<br /><em>Let’s keep it private.</em></>} body="Add the minimum details needed to attach this result to you. You can read the score immediately after this step." /><IdentityCaptureCard onComplete={() => setIdentityRequired(false)} /></div>
  if (result.fullAccess === false) return <div className="page results-page"><PageIntro eyebrow="Your results / Score ready" title={<>Your score is ready.<br /><em>Unlock the full picture.</em></>} body="You have completed the assessment. The free result shows your provisional overall score; the full report adds the seven-domain evidence and practical next steps." /><section className="panel paywall-card"><div className="result-score-head"><div><div className="eyebrow">IAQ Cognitive Profile / 0–100</div><div className="result-score">{result.composite ?? '—'}<span>{result.composite === null ? 'not enough evidence' : '/100'}</span></div></div><span className="confidence-badge">{result.confidence} confidence</span></div><div className="result-disclaimer"><div className="disclaimer-mark">!</div><div><strong>Private and provisional</strong><p>{result.disclaimer}</p></div><Link to="/methodology">Read the method ↗</Link></div><h2>{result.paywall?.title || 'Unlock your full report'}</h2><p>{result.paywall?.body || 'Unlock the detailed evaluation, interests, directions, certificate, and private email report.'}</p><div className="secondary-actions"><Link className="button primary" to={`/checkout/${result.paywall?.product_id || 'iaq-complete'}`}>Unlock full report <span>→</span></Link><Link className="text-button" to="/">Return to overview ↗</Link></div></section></div>
  const scores = result.domainScores
  const composite = result.composite
  const confidence = result.confidence
  const ranked = [...domains].sort((a, b) => (scores[b] ?? -1) - (scores[a] ?? -1))
  const metricFor = (domain: Domain) => result?.domainMetrics[domain]
  const formatTime = (milliseconds: number | null | undefined) => milliseconds ? `${(milliseconds / 1000).toFixed(1)}s median` : 'Timing not recorded'
  const scored = ranked.filter((domain) => scores[domain] !== null)
  const strongest = scored.length ? scored.slice(0, 2).join(' and ') : 'No domain has enough evidence yet'
  const lower = scored.length ? scored[scored.length - 1] : null
  return <div className="page results-page">
    <PageIntro eyebrow="Your results / Private report" title={<>See your results.<br /><em>Understand your profile.</em></>} body="This is a snapshot of how your answers compared across seven thinking areas today. It is a starting point for reflection, not a fixed label." action={<button className="button primary" onClick={() => window.print()}>Print my report <span>↗</span></button>} />
    <div className="result-disclaimer"><div className="disclaimer-mark">!</div><div><strong>Experimental IAQ Cognitive Profile / {composite ?? 'insufficient evidence'}</strong><p>{result.disclaimer}</p></div><Link to="/methodology">Read the method ↗</Link></div>
    <div className="result-grid results-top-grid"><section className="panel cognitive-panel span-8"><div className="result-score-head"><div><div className="eyebrow">Your profile score / 0–100</div><div className="result-score">{composite ?? '—'}<span>{composite === null ? 'not enough evidence' : '/100'}</span></div></div><div className="result-meta"><span className="confidence-badge">{confidence} confidence</span><span>{new Date(result.completedAt).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}</span><span>{result.assessmentVersion}</span></div></div><div className="profile-distribution"><div className="distribution-scale"><span>0</span><span>50</span><span>100</span></div>{ranked.map((domain) => { const metric = metricFor(domain); const value = scores[domain]; return <div className="distribution-row" key={domain}><div className="distribution-label"><span className={`domain-swatch ${domainMeta[domain].tone}`} /><strong>{domain}</strong><b>{value ?? 'Not assessed'}</b></div><div className="distribution-track"><i className={domainMeta[domain].tone} style={{ width: `${value ?? 0}%` }} /><span className="distribution-average" style={{ left: `${composite ?? 0}%` }} aria-hidden="true" /></div><div className="distribution-detail"><span>{metric?.correct ?? 0} of {metric?.answered ?? 0} correct</span><span>{metric?.relative || 'insufficient evidence'}</span></div></div> })}</div><div className="result-caption"><span><i className="legend-dot cobalt" /> your profile today</span><span><i className="legend-line" /> your average</span></div></section><aside className="panel result-context"><div className="eyebrow">Read the shape</div><h2>What stands out</h2><p className="result-lede"><strong>{strongest}</strong> {scored.length ? 'came through as the strongest relative signals in this attempt.' : 'need more answered items before comparison is useful.'}</p><div className="result-observation"><span className="observation-mark teal">+</span><div><strong>Strengths to notice</strong><p>{scored.length ? 'These areas came through more strongly than the rest of your profile.' : 'Complete more items in each area before drawing conclusions.'}</p></div></div><div className="result-observation"><span className="observation-mark coral">→</span><div><strong>More evidence needed</strong><p>{lower ? `${lower} is the lowest relative signal today. Treat it as a question to explore, not a verdict.` : 'Every domain needs more evidence in this result.'}</p></div></div><div className="result-context-foot"><span>Distribution is within your profile.</span><strong>No population percentile shown.</strong></div></aside></div>
    <section className="result-evidence-strip"><div><span className="eyebrow">Questions answered</span><strong>{result ? `${result.answeredCount} / ${result.questionCount}` : 'Demo view'}</strong><span>balanced across seven areas</span></div><div><span className="eyebrow">Time limit</span><strong>{result ? `${Math.ceil(result.durationSeconds / 60)} minutes` : '35 minutes'}</strong><span>the test is time-limited</span></div><div><span className="eyebrow">How to read this</span><strong>Compare the bars</strong><span>not yourself with other people</span></div></section>
    <AIInterpretationCard resultId={result.id} /><div className="result-grid result-secondary-grid"><section className="panel secondary-result-panel span-7"><div className="eyebrow">Next, when you are ready</div><h2>Explore what fits you.</h2><p>After your thinking profile, interests and real experiences can add useful context to possible directions. They do not change this result.</p><div className="secondary-actions"><Link className="button secondary" to="/interests">Tell us what you enjoy <span>→</span></Link><Link className="text-button" to="/compass">Explore directions ↗</Link></div></section><section className="panel timing-panel span-5"><div className="eyebrow">How timing affected this snapshot</div><h2>{result.quality?.status === 'acceptable' ? 'Your session looked steady.' : 'Keep timing in context.'}</h2><p>{result.quality?.warnings?.length ? `The session recorded ${result.quality.warnings.length} quality note${result.quality.warnings.length > 1 ? 's' : ''}. That does not silently change your score, but it is useful context for reading the bars.` : 'No timing warning was recorded. Faster is not automatically better; accuracy and concentration both matter.'}</p><div className="timing-note"><span className="notice-icon">i</span><span>{`Median response times are shown per domain. ${formatTime(metricFor(ranked[0])?.medianResponseTimeMs)}`}</span></div></section></div><ReportDeliveryCard resultId={result.id} />
  </div>
}

function Tracker({ savedMajors }: { savedMajors: string[] }) {
  const timeline = [{ date: '05 Sep 2026', title: 'Interest reflection saved', detail: 'I · A · C profile / Curious systems thinker', type: 'interest' }, { date: '12 Aug 2026', title: 'Cognitive profile completed', detail: '7 domains / Moderate confidence / IAQ-COG-0.3', type: 'cognitive' }, { date: '24 Jul 2026', title: 'Project evidence added', detail: 'Intro to data visualisation', type: 'evidence' }, { date: '16 Jul 2026', title: 'Started exploring Computer Science', detail: 'Overview read / Curriculum comparison pending', type: 'explore' }]
  return <div className="page"><PageIntro eyebrow="My progress / Your evidence" title={<>Track what you try.<br /><em>Notice what changes.</em></>} body="Your thinking profile should change slowly. Your interests, projects, and reflections can grow every week." action={<button className="button secondary">Add something new <span>＋</span></button>} /><div className="tracker-strip"><div><span className="eyebrow">Last thinking check-in</span><strong>24 days</strong><span>since your last test</span></div><div><span className="eyebrow">Pathway progress</span><strong>38%</strong><span>of your current plan</span></div><div><span className="eyebrow">Saved ideas</span><strong>{String(savedMajors.length || 3).padStart(2, '0')}</strong><span>to revisit this month</span></div><div className="tracker-note"><span className="notice-icon">i</span><span>Next thinking check-in: <strong>12 May 2027</strong>. Testing too often can make practice look like progress.</span></div></div><div className="tracker-layout"><section className="panel timeline-panel"><div className="panel-top"><div><div className="eyebrow">Your recent activity</div><h2>What you have done</h2></div><button className="text-button">Filter ↕</button></div><div className="timeline">{timeline.map((item) => <div className="timeline-item" key={item.date + item.title}><div className={`timeline-node ${item.type}`} /> <div className="timeline-date">{item.date}</div><div className="timeline-content"><h3>{item.title}</h3><p>{item.detail}</p></div><button className="timeline-more">···</button></div>)}</div></section><aside className="panel explorer-panel"><div className="eyebrow">Your current path</div><h2>Computer Science</h2><span className="explorer-progress">2 / 6 steps</span><div className="explorer-list">{['Read the overview', 'Compare university courses', 'Try a coding lesson', 'Build a small app', 'Talk to a CS student', 'Write a reflection'].map((item, i) => <div key={item} className={i < 2 ? 'done' : ''}><span>{i < 2 ? '✓' : '○'}</span>{item}</div>)}</div><button className="button primary full">Continue my path <span>→</span></button></aside></div><section className="snapshot-section"><div className="eyebrow">Your check-ins</div><h2>Four ways to see your progress</h2><div className="snapshot-grid"><Snapshot title="Thinking history" value="07" detail="areas / 1 test" tone="blue" /><Snapshot title="Interest changes" value="IAC" detail="top-three code" tone="orange" /><Snapshot title="School & projects" value="05" detail="things added" tone="teal" /><Snapshot title="Your reflections" value="01" detail="one waiting for you" tone="coral" /></div></section></div>
}
function Snapshot({ title, value, detail, tone }: { title: string; value: string; detail: string; tone: string }) { return <div className={`snapshot ${tone}`}><span>{title}</span><strong>{value}</strong><small>{detail}</small><span className="snapshot-arrow">↗</span></div> }

function School() {
  const students = [{ initials: 'LS', name: 'Lena Suryani', grade: 'Grade 11 · consented', status: 'Complete', direction: 'Design & technology', confidence: 'High' }, { initials: 'FK', name: 'Fajar Kusuma', grade: 'Grade 10 · consented', status: 'In progress', direction: '—', confidence: 'Pending' }, { initials: 'NA', name: 'Nadia Arum', grade: 'Grade 12 · consented', status: 'Complete', direction: 'People & behaviour', confidence: 'Moderate' }, { initials: 'RW', name: 'Raka Wijaya', grade: 'Grade 11 · access pending', status: 'Awaiting consent', direction: '—', confidence: '—' }]
  return <div className="page ops-page"><PageIntro eyebrow="Counselor dashboard / School view" title={<>See the group.<br /><em>Support each person.</em></>} body="A focused view for authorized counselors. No rankings — just the context needed for a helpful conversation." action={<button className="button primary">Download summary <span>↓</span></button>} /><div className="ops-kpis"><Kpi label="Tests finished" value="72%" detail="18 of 25 students" /><Kpi label="Needs a follow-up" value="04" detail="low-confidence sessions" /><Kpi label="Popular direction" value="Design" detail="8 students exploring" /><Kpi label="Common gap" value="Math" detail="most mentioned" /></div><section className="panel table-panel"><div className="table-head"><div><div className="eyebrow">Authorized students / 25</div><h2>Who needs your attention?</h2></div><div className="filter-row"><button className="filter active">Everyone</button><button className="filter">Needs attention</button></div></div><div className="student-table"><div className="student-row table-label"><span>Student</span><span>Test status</span><span>Exploring</span><span>Confidence</span><span /></div>{students.map((student) => <div className="student-row" key={student.name}><div className="student-cell"><div className="avatar small">{student.initials}</div><div><strong>{student.name}</strong><span>{student.grade}</span></div></div><span className={`table-status ${student.status.toLowerCase().replaceAll(' ', '-')}`}>{student.status}</span><span>{student.direction}</span><span className={`confidence-text ${student.confidence.toLowerCase()}`}>{student.confidence}</span><button className="table-action">Open report ↗</button></div>)}</div></section><section className="cohort-grid"><div className="panel cohort-chart"><div className="eyebrow">A private, anonymized summary</div><h2>What students are exploring</h2><div className="cohort-chart-inner"><ResponsiveContainer width="65%" height={190}><PieChart><Pie data={[{ name: 'Design', value: 8 }, { name: 'Technology', value: 7 }, { name: 'People', value: 5 }, { name: 'Science', value: 3 }, { name: 'Other', value: 2 }]} innerRadius={58} outerRadius={82} dataKey="value" stroke="none">{['#315CFF', '#1AAE91', '#F56B5D', '#E5A43A', '#D7D2C7'].map((color) => <Cell fill={color} key={color} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer><div className="pie-legend"><span><i style={{ background: '#315CFF' }} />Design <b>8</b></span><span><i style={{ background: '#1AAE91' }} />Technology <b>7</b></span><span><i style={{ background: '#F56B5D' }} />People <b>5</b></span><span><i style={{ background: '#E5A43A' }} />Science <b>3</b></span></div></div></div><div className="panel counselor-note"><div className="eyebrow">Privacy reminder</div><h2>Permission comes first.</h2><p>Only students who grant access appear here. Every report view is logged so trust stays part of the experience.</p><button className="text-button">Read access rules ↗</button></div></section></div>
}
function Kpi({ label, value, detail }: { label: string; value: string; detail: string }) { return <div className="kpi"><span>{label}</span><strong>{value}</strong><small>{detail}</small></div> }

function Admin() {
  const items = [{ id: 'GF-MAT-001', title: 'Matrix rotation / count', domain: 'Abstract reasoning', status: 'Active', responses: 342, difficulty: '0.62', flag: '' }, { id: 'LOG-081', title: 'Conditional studio logic', domain: 'Deductive logic', status: 'Pilot', responses: 84, difficulty: '0.48', flag: 'Low discrimination' }, { id: 'NUM-024', title: 'Exponential sequence', domain: 'Numerical reasoning', status: 'Review', responses: 0, difficulty: '—', flag: 'Insufficient data' }, { id: 'VRB-017', title: 'Evidence and inference', domain: 'Verbal reasoning', status: 'Active', responses: 219, difficulty: '0.71', flag: '' }]
  return <div className="page ops-page"><PageIntro eyebrow="Question studio / Content review" title={<>Make every question<br /><em>worth asking.</em></>} body="Manage reviewed questions, check how they are behaving, and keep early experiments separate from real evidence." action={<button className="button primary">Add a question <span>＋</span></button>} /><div className="studio-banner"><div><span className="eyebrow">Question journey</span><strong>Draft → Checked → Reviewed → Pilot → Calibrated → Live</strong></div><span className="mono-label">12 live / 06 to review</span></div><section className="panel item-table-panel"><div className="table-head"><div><div className="eyebrow">Question bank / versioned</div><h2>How are the questions doing?</h2></div><div className="filter-row"><button className="filter active">All questions</button><button className="filter">Needs review</button><button className="filter">＋ Filter</button></div></div><div className="item-table"><div className="item-row item-label"><span>Question</span><span>Thinking area</span><span>Status</span><span>Answers</span><span>Difficulty</span><span>Health</span><span /></div>{items.map((item) => <div className="item-row" key={item.id}><div><span className="mono-label">{item.id} / V1</span><strong>{item.title}</strong></div><span>{item.domain}</span><span className={`lifecycle ${item.status.toLowerCase()}`}>{item.status}</span><span className="mono-value">{item.responses || '—'}</span><span className="mono-value">{item.difficulty}</span><span className={item.flag ? 'health-flag' : 'health-good'}>{item.flag || 'Healthy'}</span><button className="table-action">Open ↗</button></div>)}</div></section><div className="admin-bottom"><section className="panel item-detail"><div className="eyebrow">Selected question / LOG-081</div><h2>Conditional studio logic</h2><p>“If the studio is open, the green light is on. The green light is off. Which conclusion is safest?”</p><div className="answer-preview"><span className="correct">A</span><span>It is closed</span><span className="answer-key">answer key / protected</span></div><div className="detail-stats"><Metric label="Correct rate" value={48} /><Metric label="Separates levels" value={31} /><Metric label="Confusion reports" value={18} /></div></section><section className="panel review-queue"><div className="eyebrow">Review queue / 03</div><h2>Needs a second look</h2><div className="queue-list"><div><span className="queue-dot coral" /><span><strong>LOG-081</strong> not separating well</span><b>→</b></div><div><span className="queue-dot orange" /><span><strong>VIS-033</strong> screen issue</span><b>→</b></div><div><span className="queue-dot blue" /><span><strong>NUM-024</strong> not enough answers yet</span><b>→</b></div></div><button className="text-button">Open review queue ↗</button></section></div></div>
}

function FAQSection() {
  const questions = [{ question: 'Is this an official IQ test?', answer: 'No. IAQ is an experimental educational profile that compares your own domain signals. It is not a diagnosis, population percentile, or officially normed IQ score.' }, { question: 'Why is the test timed?', answer: 'The 35-minute limit creates a consistent snapshot of accuracy and timing. Your report keeps timing context visible instead of treating speed as a verdict.' }, { question: 'Can my result change?', answer: 'Yes. A later attempt can look different because of focus, familiarity, fatigue, and the questions selected. That is why we show evidence and confidence.' }, { question: 'What happens to my answers?', answer: 'Responses are used to calculate your private report. Synthetic data is kept separate from real pilot responses, and report email is optional.' }]
  return <section className="faq-section"><div><div className="eyebrow">Questions students ask</div><h2>Clear answers before you begin.</h2></div><div className="faq-list">{questions.map((item) => <details key={item.question}><summary>{item.question}<span>＋</span></summary><p>{item.answer}</p></details>)}</div></section>
}

function Methodology() { return <div className="page legal-page"><PageIntro eyebrow="IAQ / Methodology" title={<>Useful now.<br /><em>Honest about limits.</em></>} body="IAQ V1.0 is designed as an early educational product. It is built to become more evidence-based through real pilots, not to simulate scientific certainty." /><div className="legal-grid"><section><div className="eyebrow">01 / What we measure</div><h2>Seven cognitive domains, one relative profile.</h2><p>We show how signals compare within your own profile. We do not show population percentiles, a fake bell curve, or a clinical IQ diagnosis.</p>{domains.map((domain, i) => <div className="method-row" key={domain}><span>0{i + 1}</span><strong>{domain}</strong><p>{domainMeta[domain].description}</p></div>)}</section><section className="legal-callout"><span className="notice-icon">i</span><h2>Content can be generated. Evidence cannot.</h2><p>AI may help draft candidates, distractors, or explanations. Real student responses are required to estimate difficulty, discrimination, fairness, and predictive value.</p><div className="method-steps"><span><b>01</b> reviewed families</span><span><b>02</b> deterministic variants</span><span><b>03</b> human review</span><span><b>04</b> real pilot data</span></div></section></div><FAQSection /><div className="legal-footer"><Link to="/privacy">Read privacy model ↗</Link><Link to="/">Return to overview ↗</Link></div></div> }
function Privacy() { return <div className="page legal-page"><PageIntro eyebrow="IAQ / Privacy model" title={<>A profile should<br /><em>belong to you.</em></>} body="We design for minors, consent, and the minimum useful data. Demo mode keeps everything in this browser." /><div className="privacy-grid">{[{ title: 'Consent first', body: 'Assessment access requires a clear consent record and versioned notice. Guardian support is part of the production data model.' }, { title: 'Identity apart', body: 'Identity and research response data are separate concepts. Export and deletion flows are planned as first-class product capabilities.' }, { title: 'No surveillance', body: 'No camera, microphone, eye tracking, emotion detection, or secret behavioural inference is used.' }, { title: 'Human context', body: 'Reports explain signals and uncertainty. They do not diagnose, decide a student’s future, or rank students publicly.' }].map((item, i) => <div className="privacy-card" key={item.title}><span>0{i + 1}</span><h2>{item.title}</h2><p>{item.body}</p></div>)}</div><div className="notice-bar"><span className="notice-icon">!</span><span><strong>Demo mode note.</strong> This local preview uses seeded example data. Configure a production database, authentication provider, encryption, and retention policy before collecting real student responses.</span></div></div> }

export default App
