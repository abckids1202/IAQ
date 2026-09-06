import { useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts'
import { Link, NavLink, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { alternatives, domainMeta, domains, initialScores, majors, questions, recommendations } from './data'
import { finishAssessment, saveAndGetNext, startRandomizedAssessment } from './api'
import type { AssessmentResult, Domain, Major, Profile, Question, Role } from './types'

const initialProfile: Profile = {
  name: 'Ari Pratama', completed: true, consented: true, role: 'student', lastAssessment: '12 Aug 2026', nextAssessment: '12 May 2027', strengths: ['Visual-spatial reasoning', 'Abstract reasoning'], scores: initialScores
}

function App() {
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
    setProfile((current) => ({ ...current, completed: true, lastAssessment: new Date(result.completedAt).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }), composite: result.composite, confidence: result.confidence, scores: result.domainScores, strengths: [...domains].sort((a, b) => result.domainScores[b] - result.domainScores[a]).slice(0, 2), lastResult: result }))
    setAssessmentComplete(true)
  }

  return <Routes>
    <Route path="/welcome" element={<PublicSite />} />
    <Route path="/" element={<StudentAppShell profile={profile}><Home profile={profile} savedMajors={savedMajors} /></StudentAppShell>} />
    <Route path="/assess" element={<StudentAppShell profile={profile}><AssessLanding /></StudentAppShell>} />
    <Route path="/assess/session" element={<Assessment onComplete={completeAssessment} />} />
    <Route path="/compass" element={<StudentAppShell profile={profile}><Compass savedMajors={savedMajors} toggleMajor={toggleMajor} /></StudentAppShell>} />
    <Route path="/tracker" element={<StudentAppShell profile={profile}><Tracker savedMajors={savedMajors} /></StudentAppShell>} />
    <Route path="/results" element={<StudentAppShell profile={profile}><Results profile={profile} savedMajors={savedMajors} toggleMajor={toggleMajor} /></StudentAppShell>} />
    <Route path="/school" element={<CounselorAppShell><School /></CounselorAppShell>} />
    <Route path="/admin" element={<AdminAppShell><Admin /></AdminAppShell>} />
    <Route path="/methodology" element={<StudentAppShell profile={profile}><Methodology /></StudentAppShell>} />
    <Route path="/privacy" element={<StudentAppShell profile={profile}><Privacy /></StudentAppShell>} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>
}

const studentNav = [
  { to: '/', label: 'Overview', icon: '⌂', end: true },
  { to: '/assess', label: 'Take a test', icon: '◈' },
  { to: '/results', label: 'Your results', icon: '↗' },
  { to: '/compass', label: 'Explore directions', icon: '✦' },
  { to: '/tracker', label: 'Your progress', icon: '◒' }
]

function pageName(pathname: string) {
  const names: Record<string, string> = { '/': 'Overview', '/assess': 'Take a test', '/compass': 'Explore directions', '/tracker': 'Your progress', '/results': 'Your results', '/school': 'Overview', '/admin': 'Overview', '/methodology': 'Help & Methodology', '/privacy': 'Privacy' }
  return names[pathname] || pathname.slice(1).replaceAll('-', ' ')
}

function Brand({ to = '/' }: { to?: string }) {
  return <Link to={to} className="brand"><span className="brand-mark">i</span><span>IAQ</span><span className="brand-dot">·</span></Link>
}

function WorkspaceSwitcher({ active }: { active: string }) {
  return <div className="workspace-switcher"><Brand /><span className="workspace-divider">/</span><details><summary>{active}<span className="workspace-chevron">⌄</span></summary><div className="workspace-menu"><Link to="/">Student Profile</Link><Link to="/school">Counselor Workspace</Link><Link to="/admin">Administration</Link><Link to="/welcome">Public Website</Link></div></details></div>
}

function ProfileMenu({ profile, label }: { profile?: Profile; label: string }) {
  return <details className="profile-menu"><summary><div className="avatar">AP</div><div><strong>{profile?.name || 'Ari Pratama'}</strong><span>{label}</span></div><span className="profile-chevron">⌄</span></summary><div className="profile-popover"><Link to="/methodology">Help & Methodology</Link><Link to="/privacy">Privacy</Link><Link to="/welcome">Sign out</Link></div></details>
}

function StudentAppHeader({ profile }: { profile: Profile }) {
  return <header className="student-header"><div className="student-header-inner"><WorkspaceSwitcher active="Student Profile" /><nav className="student-nav" aria-label="Student navigation">{studentNav.map((item) => <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => `student-nav-link ${isActive ? 'active' : ''}`}><span className="student-nav-icon">{item.icon}</span>{item.label}</NavLink>)}</nav><div className="student-utilities"><Link to="/methodology" className="help-link">Help</Link><ProfileMenu profile={profile} label="Student profile" /></div></div></header>
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
  const links = [{ to: '/methodology', label: 'How it works' }, { to: '/assess', label: 'Assessments' }, { to: '/compass', label: 'Explore directions' }, { to: '/welcome#schools', label: 'For schools' }, { to: '/methodology', label: 'Methodology' }]
  return <header className="public-navbar"><div className="public-navbar-inner"><Brand to="/welcome" /><nav aria-label="Public navigation">{links.map((link) => <Link key={link.label} to={link.to}>{link.label}</Link>)}</nav><button className="public-menu-toggle" onClick={() => setMobileOpen((value) => !value)} aria-expanded={mobileOpen}>Menu</button><div className="public-actions"><Link to="/" className="public-sign-in">Sign in</Link><Link to="/assess" className="button primary">Take a test <span>→</span></Link></div></div>{mobileOpen && <nav className="public-mobile-menu" aria-label="Mobile public navigation">{links.map((link) => <Link key={link.label} to={link.to} onClick={() => setMobileOpen(false)}>{link.label}</Link>)}</nav>}</header>
}

function PublicSite() {
  return <div className="public-site"><PublicNavbar /><main className="public-main"><div className="public-kicker">A clearer way to start thinking about what comes next</div><h1>See how you think.<br /><em>Find your next direction.</em></h1><p>IAQ brings together thinking patterns, interests, and real experiences to help students explore their potential.</p><div className="public-actions-large"><Link to="/assess" className="button primary">Start your assessment <span>→</span></Link><Link to="/methodology" className="text-button">How it works ↗</Link></div><div className="public-cards"><section><span>01 / THINKING</span><h2>Understand your strengths.</h2><p>Explore seven kinds of thinking without reducing you to one number.</p></section><section id="schools"><span>02 / SCHOOLS</span><h2>Give every student context.</h2><p>Support better conversations with consent-aware student and counselor workspaces.</p></section><section><span>03 / DIRECTION</span><h2>Make a next step feel possible.</h2><p>Compare major ideas, try small experiments, and build evidence over time.</p></section></div></main></div>
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
  const composite = profile.composite || Math.round(domains.reduce((total, domain) => total + profile.scores[domain], 0) / domains.length)
  const ranked = [...domains].sort((a, b) => profile.scores[b] - profile.scores[a])
  return <div className="page home-page">
    <PageIntro eyebrow="Your starting point" title={hasResult ? <>Your thinking profile<br /><em>is ready to explore.</em></> : <>Start with one test.<br /><em>Learn how you think.</em></>} body={hasResult ? 'Your result is a private snapshot across seven thinking areas. Read it first, then decide what you want to explore next.' : 'Take the timed IAQ assessment to get a clear, visual snapshot of seven different thinking areas.'} action={<Link to={hasResult ? '/results' : '/assess'} className="button primary">{hasResult ? 'See your results' : 'Take a test'} <span>→</span></Link>} />
    <div className="notice-bar"><span className="notice-icon">i</span><span><strong>Experimental profile.</strong> IAQ results are educational and provisional. They are not a clinical diagnosis or an officially normed IQ score.</span><Link to="/methodology">Read the method ↗</Link></div>
    <div className="dashboard-grid home-grid"><section className="panel home-result-preview span-8"><div className="panel-top"><div><div className="eyebrow">Latest result / seven areas</div><h2>{hasResult ? 'Your profile at a glance' : 'Your result will live here'}</h2></div><span className="mono-label">{hasResult ? profile.lastAssessment : 'NOT STARTED'}</span></div><div className="home-result-body"><div className="home-score"><span>{hasResult ? 'IAQ profile score' : 'Ready when you are'}</span><strong>{hasResult ? composite : '—'}{hasResult && <small>/100</small>}</strong><p>{hasResult ? `${profile.confidence || 'moderate'} confidence · within-profile only` : 'Complete the timed test to see your distribution.'}</p></div><div className="home-bars" aria-label="Thinking profile preview">{ranked.map((domain) => <div className="home-bar-row" key={domain}><span>{domainMeta[domain].short}</span><i><b className={domainMeta[domain].tone} style={{ width: `${hasResult ? profile.scores[domain] : 0}%` }} /></i><strong>{hasResult ? profile.scores[domain] : '—'}</strong></div>)}</div></div><div className="panel-footer"><span>{hasResult ? `Strongest today: ${profile.strengths.join(' + ')}` : '56 questions · 35 minutes · randomized'}</span><Link to={hasResult ? '/results' : '/assess'}>{hasResult ? 'Read the full report ↗' : 'See what is included ↗'}</Link></div></section><aside className="panel home-start-panel span-4"><div className="eyebrow">What happens next</div><div className="home-step-number">01</div><h2>{hasResult ? 'Add context later.' : 'Take the test first.'}</h2><p>{hasResult ? 'Interests, projects, and possible directions become more useful after you understand the cognitive snapshot.' : 'Find a quiet place. Answer 56 medium-to-hard tasks. Your result appears immediately when you finish.'}</p><Link className="button secondary full" to={hasResult ? '/compass' : '/assess'}>{hasResult ? 'Explore directions' : 'Start the test'} <span>→</span></Link></aside><section className="panel home-next-panel span-12"><div><div className="eyebrow">After your result</div><h2>Explore what you want to know next.</h2><p>IAQ can later connect your profile to interests, subjects, and real experiences — without turning one score into a prediction of your future.</p></div><div className="home-next-links"><Link to="/compass"><span>01</span>Explore directions <b>↗</b></Link><Link to="/tracker"><span>02</span>Check your progress <b>↗</b></Link><Link to="/methodology"><span>03</span>Understand the method <b>↗</b></Link></div></section></div>
  </div>
}

function EvidenceRow({ label, value, state }: { label: string; value: string; state: string }) { return <div className="evidence-row"><span className={`state-mark ${state}`}>{state === 'good' ? '✓' : '○'}</span><span>{label}</span><strong>{value}</strong></div> }

function AssessLanding() {
  return <div className="page"><PageIntro eyebrow="Take a test / 35 minutes" title={<>Take a test.<br /><em>See your thinking profile.</em></>} body="Answer 56 medium-to-hard tasks across seven thinking areas. Find a quiet place, keep your focus, and use your result as a starting point — not a label." action={<Link to="/assess/session" className="button primary">Start my test <span>→</span></Link>} /><div className="notice-bar subtle"><span className="notice-icon">⌁</span><span><strong>Before you begin.</strong> You will have 35 minutes. The test is timed and submits automatically when time runs out.</span></div><div className="assessment-overview"><section className="assessment-hero"><div className="assessment-index">01 <span>/ 07</span></div><h2>Seven ways to see<br /><em>how you think.</em></h2><p>We look at different kinds of thinking so one number never has to tell the whole story.</p><Link to="/methodology" className="text-button light">See how it works ↗</Link></section><div className="domain-list">{domains.map((domain, index) => <div className="domain-row" key={domain}><span className="domain-no">0{index + 1}</span><div><strong>{domain}</strong><span>{domainMeta[domain].description}</span></div><span className={`domain-tag ${domainMeta[domain].tone}`}>{index === 5 ? '8 memory tasks' : index === 6 ? '8 speed tasks' : '8 questions'}</span></div>)}</div></div></div>
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
  return <div className="assessment-screen"><header className="assessment-header"><div className="assessment-brand"><Brand /><span className="assessment-name">IAQ Cognitive Profile</span></div><div className="assessment-progress"><span>Assessment progress</span><div className="progress-track"><span style={{ width: `${Math.max(5, progress)}%` }} /></div><span className="mono-label">{String(Math.min(displayNumber, totalQuestions)).padStart(2, '0')} / {totalQuestions}</span></div><div className="assessment-actions"><button className="text-button" onClick={() => setPaused(true)}>Pause</button><button className="text-button" onClick={() => setApiError('Technical issue noted. If this continues, exit and restart the assessment.')}>Report issue</button><Link className="assessment-exit" to="/">Exit assessment</Link></div></header><main className="assessment-main"><div className="assessment-meta"><span className="eyebrow">Question {String(Math.min(displayNumber, totalQuestions)).padStart(2, '0')} / {question.domain}</span><span className="timer-label">◷ {Math.max(1, Math.floor((Date.now() - startedAt) / 60000))} min</span></div><AnimatePresence mode="wait"><motion.div key={question.id} className="question-card" initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -18 }} transition={{ duration: .2 }}><div className="question-copy"><h1>{question.prompt}</h1>{question.helper && <p>{question.helper}</p>}</div>{question.visual && <div className="stimulus"><div className="stimulus-grid">{question.visual.map((item) => <span key={item}>{item}</span>)}</div><span className="stimulus-note">visual stimulus</span></div>}<div className="option-grid">{question.options.map((option, optionIndex) => <button key={option} className={`option ${selected === option ? 'selected' : ''}`} onClick={() => choose(option)}><span className="option-letter">{String.fromCharCode(65 + optionIndex)}</span><span>{option}</span><span className="option-check">{selected === option ? '✓' : ''}</span></button>)}</div></motion.div></AnimatePresence><div className="assessment-controls"><button className="button ghost" disabled={usingApi || index === 0} onClick={() => setIndex((i) => Math.max(0, i - 1))}>← Previous</button><span className="autosave">{selected ? (usingApi ? 'Ready to save' : 'Answer saved locally') : 'Select one answer to continue'}</span><button className="button primary" disabled={!selected || submitting} onClick={next}>{submitting ? 'Saving…' : displayNumber === totalQuestions ? 'See profile' : 'Continue'} <span>→</span></button></div>{apiError && <div className="assessment-inline-error">{apiError}</div>}<div className="assessment-footnote">{usingApi ? '56 questions / 8 from each thinking area / randomized for this attempt.' : 'Demo fallback / 14 questions / start the IAQ API for a randomized 56-question form.'}</div></main>{paused && <div className="modal-backdrop"><div className="modal"><button className="modal-close" onClick={() => setPaused(false)} aria-label="Close">×</button><div className="eyebrow">Session saved</div><h2>Your progress is safe.</h2><p>You have answered {answered} of {totalQuestions} questions. Resume when you have a quiet moment.</p><div className="modal-actions"><button className="button ghost" onClick={() => setPaused(false)}>Keep going</button><button className="button primary" onClick={() => { setPaused(false); navigate('/') }}>Exit assessment</button></div><button className="text-button" onClick={restart}>Restart this test</button></div></div>}</div>
}

function Assessment({ onComplete }: { onComplete: (result: AssessmentResult) => void }) {
  const navigate = useNavigate()
  const submissionStarted = useRef(false)
  const [apiSession, setApiSession] = useState<string | null>(null)
  const [question, setQuestion] = useState<Question | null>(null)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [questionStartedAt, setQuestionStartedAt] = useState(Date.now())
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
      const started = await startRandomizedAssessment()
      setApiSession(started.sessionId)
      setQuestion(started.question)
      setDeadlineAt(started.deadlineAt)
      setTimeLeft(Math.max(0, Math.ceil((new Date(started.deadlineAt).getTime() - Date.now()) / 1000)))
      setTotalQuestions(started.questionCount)
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
  const answered = Math.max(0, Object.keys(answers).length - currentSelection)
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
  return <div className="assessment-screen"><header className="assessment-header"><div className="assessment-brand"><Brand /><span className="assessment-name">IAQ Cognitive Profile</span></div><div className="assessment-progress"><span>Progress</span><div className="progress-track"><span style={{ width: `${Math.max(3, progress)}%` }} /></div><span className="mono-label">{String(Math.min(answered + 1, totalQuestions)).padStart(2, '0')} / {totalQuestions}</span></div><div className="assessment-actions"><button className="text-button" onClick={() => setApiError('Your test is timed. If you leave, the countdown continues.')}>Need help?</button><Link className="assessment-exit" to="/">Leave test</Link></div></header><main className="assessment-main"><div className="assessment-meta"><span className="eyebrow">Question {String(Math.min(answered + 1, totalQuestions)).padStart(2, '0')} / {question.domain}</span><span className={`timer-label ${timerClass}`} aria-live="polite">Time left {minutes}:{seconds}</span></div>{timeLeft <= 600 && <div className={`timer-notice ${timerClass}`}>{timeLeft <= 300 ? 'Five minutes left. Choose your best answer and keep moving.' : 'Ten minutes left. Keep an eye on the clock.'}</div>}<AnimatePresence mode="wait"><motion.div key={question.id} className="question-card" initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -18 }} transition={{ duration: .2 }}><div className="question-copy"><h1>{question.prompt}</h1>{question.helper && <p>{question.helper}</p>}</div>{question.visual && <div className="stimulus" aria-label="Visual stimulus"><div className="stimulus-grid">{question.visual.map((item) => <span key={item}>{item}</span>)}</div><span className="stimulus-note">visual stimulus</span></div>}<div className="option-grid">{question.options.map((option, optionIndex) => <button key={option} className={`option ${selected === option ? 'selected' : ''}`} onClick={() => choose(option)} aria-pressed={selected === option}><span className="option-letter">{String.fromCharCode(65 + optionIndex)}</span><span>{option}</span><span className="option-check">{selected === option ? '✓' : ''}</span></button>)}</div></motion.div></AnimatePresence><div className="assessment-controls"><span className="autosave">{selected ? 'Answer ready' : 'Choose one answer to continue'}</span><button className="button primary" disabled={!selected || submitting || timeLeft === 0} onClick={next}>{submitting ? 'Saving…' : answered + 1 >= totalQuestions ? 'See my results' : 'Next question'} <span>→</span></button></div>{apiError && <div className="assessment-inline-error" role="alert">{apiError}</div>}<div className="assessment-footnote">35 minutes total · 8 questions from each thinking area · your answers are saved as you go.</div></main></div>
}

function Compass({ savedMajors, toggleMajor }: { savedMajors: string[]; toggleMajor: (name: string) => void }) {
  const [filter, setFilter] = useState('All directions')
  const filters = ['All directions', 'Technology', 'Design', 'People & behaviour']
  const shown = filter === 'All directions' ? majors : majors.filter((major) => major.family.toLowerCase().includes(filter.split(' ')[0].toLowerCase()))
  return <div className="page"><PageIntro eyebrow="Find your path / Explore ideas" title={<>Explore what could<br /><em>fit you.</em></>} body="Tell us what you enjoy, then compare possible paths by fit, readiness, and what you could try next." action={<button className="button primary" onClick={() => document.getElementById('questionnaire')?.scrollIntoView({ behavior: 'smooth' })}>Tell us what you like <span>↓</span></button>} /><div className="compass-summary"><div><span className="eyebrow">Your interest code</span><div className="riasec-code">I<span>A</span>C</div><p>Investigative · Artistic · Conventional</p></div><div className="compass-summary-copy"><strong>You like ideas that make sense.</strong><span>You seem drawn to understanding how things work, making ideas visible, and turning messy information into something useful.</span></div><div className="riasec-mini">{['R', 'I', 'A', 'S', 'E', 'C'].map((code, i) => <div key={code}><span>{code}</span><i style={{ height: `${[34, 92, 78, 42, 28, 65][i]}%` }} /></div>)}</div></div><section className="major-explorer"><div className="explorer-head"><div><div className="eyebrow">Five ideas / explained simply</div><h2>What sounds interesting?</h2></div><div className="filter-row">{filters.map((item) => <button key={item} className={filter === item ? 'filter active' : 'filter'} onClick={() => setFilter(item)}>{item}</button>)}</div></div><div className="major-grid">{shown.map((major) => <MajorCard key={major.name} major={major} saved={savedMajors.includes(major.name)} onSave={() => toggleMajor(major.name)} />)}</div></section><section className="questionnaire" id="questionnaire"><div><div className="eyebrow">One quick question</div><h2>Make your profile more you.</h2><p>Interests can change. Tell us what you enjoy doing, not what you think you should choose.</p></div><div className="question-card compact"><span className="eyebrow">When you have a free afternoon, what sounds most satisfying?</span><div className="questionnaire-options">{['Make something visual', 'Solve a puzzling problem', 'Help someone untangle a problem', 'Organise an idea or plan'].map((item, i) => <button key={item} onClick={(e) => { (e.currentTarget as HTMLButtonElement).classList.toggle('selected') }}><span>{String.fromCharCode(65 + i)}</span>{item}</button>)}</div><button className="button primary small">Save my answer <span>→</span></button></div></section></div>
}

function MajorCard({ major, saved, onSave }: { major: Major; saved: boolean; onSave: () => void }) { return <article className="major-card" style={{ '--accent': major.accent } as React.CSSProperties}><div className="major-card-accent" /><div className="major-head"><div><span className="eyebrow">{major.family}</span><h3>{major.name}</h3></div><button className={`save-button ${saved ? 'saved' : ''}`} onClick={onSave} aria-label={saved ? `Remove ${major.name}` : `Save ${major.name}`}>{saved ? '★' : '☆'}</button></div><p>{major.reason}</p><div className="major-metrics"><Metric label="Fit" value={major.fit} /><Metric label="Ready now" value={major.readiness} /><Metric label="Confidence" value={major.confidence} /></div><div className="major-card-foot"><span className={`feasibility ${major.feasibility.toLowerCase().replaceAll(' ', '-')}`}>{major.feasibility}</span><button className="text-button">Explore ↗</button></div></article> }
function Metric({ label, value }: { label: string; value: number }) { return <div className="metric"><span>{label}</span><strong>{value}</strong><div className="metric-bar"><i style={{ width: `${value}%` }} /></div></div> }

function LegacyResults({ profile, savedMajors, toggleMajor }: { profile: Profile; savedMajors: string[]; toggleMajor: (name: string) => void }) {
  const chartData = domains.map((domain) => ({ subject: domainMeta[domain].short, score: profile.scores[domain] }))
  const fitData = majors.map((major) => ({ x: major.fit, y: major.readiness, name: major.name, fill: major.accent }))
  return <div className="page"><PageIntro eyebrow="See your potential / Your report" title={<>See your potential.<br /><em>Keep exploring.</em></>} body="Here is a simple snapshot of how you think, what interests you, and what you could try next." action={<button className="button primary" onClick={() => window.print()}>Print my report <span>↗</span></button>} /><div className="result-disclaimer"><div className="disclaimer-mark">!</div><div><strong>Experimental IAQ Composite / 74</strong><p>This V1.0 result is an experimental educational profile, not a clinical diagnosis or officially normed IQ score. It should support reflection and conversation.</p></div><Link to="/methodology">Why this matters ↗</Link></div><div className="result-grid"><section className="panel cognitive-panel span-7"><div className="panel-top"><div><div className="eyebrow">Your thinking snapshot / 07 areas</div><h2>How you think today</h2></div><span className="confidence-badge">Moderate confidence</span></div><div className="domain-bars">{domains.map((domain) => <div className="result-domain" key={domain}><div className="result-domain-label"><span>{domain}</span><b>{profile.scores[domain]}</b></div><div className="result-bar"><i className={domainMeta[domain].tone} style={{ width: `${profile.scores[domain]}%` }} /><span style={{ left: `${profile.scores[domain]}%` }} /></div><p>{domainMeta[domain].description}</p></div>)}</div><div className="result-caption"><span><i className="legend-dot cobalt" /> your profile today</span><span><i className="legend-line" /> no population percentile shown</span></div></section><section className="panel chart-panel span-5"><div className="eyebrow">A quick look</div><h2>Your strengths, side by side</h2><p className="muted">Spatial and abstract tasks stand out today. Speed is a developing signal — it deserves context, not a fixed label.</p><div className="radar-like"><ResponsiveContainer width="100%" height={230}><AreaChart data={chartData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}><CartesianGrid stroke="#e5e1d8" vertical={false} /><XAxis dataKey="subject" tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: '#72746e' }} /><YAxis domain={[0, 100]} tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: '#9c9b93' }} /><Area type="monotone" dataKey="score" stroke="#315CFF" fill="#315CFF" fillOpacity={.1} strokeWidth={2} /><ReferenceLine y={74} stroke="#1AAE91" strokeDasharray="4 4" /></AreaChart></ResponsiveContainer></div><Link to="/tracker" className="text-button">See my progress ↗</Link></section><section className="panel interest-panel span-5"><div className="eyebrow">What interests you</div><div className="interest-head"><h2>I · A · C</h2><span>top three</span></div><p><strong>You like ideas that make sense.</strong> You may enjoy understanding how things work, making ideas visible, and bringing structure to open-ended problems.</p><div className="interest-bars">{['Investigative', 'Artistic', 'Conventional', 'Realistic', 'Social', 'Enterprising'].map((item, i) => <div key={item}><span>{item}</span><i><b style={{ width: `${[92, 78, 65, 42, 35, 28][i]}%` }} /></i></div>)}</div><span className="muted tiny">Your interests can change as you try real things.</span></section><section className="panel fit-panel span-7"><div className="panel-top"><div><div className="eyebrow">Paths you could explore</div><h2>What might fit you?</h2></div><span className="mono-label">5 ideas / 3 alternatives</span></div><p className="muted">Fit is how well a path matches your profile. Readiness is what you have evidence for today. Neither is a permanent limit.</p><div className="fit-chart"><ResponsiveContainer width="100%" height={250}><ScatterChart margin={{ top: 20, right: 30, bottom: 20, left: -12 }}><CartesianGrid stroke="#e3dfd5" /><XAxis type="number" dataKey="x" domain={[50, 100]} tick={{ fontSize: 10 }} tickLine={false} axisLine={false} label={{ value: 'Fit →', position: 'insideBottom', offset: -10, fontSize: 10 }} /><YAxis type="number" dataKey="y" domain={[45, 100]} tick={{ fontSize: 10 }} tickLine={false} axisLine={false} label={{ value: 'Ready now', angle: -90, position: 'insideLeft', fontSize: 10 }} /><Tooltip cursor={{ strokeDasharray: '3 3' }} content={({ active, payload }) => active && payload?.[0] ? <div className="scatter-tooltip">{payload[0].payload.name}<strong>{payload[0].payload.x} fit · {payload[0].payload.y} ready</strong></div> : null} /><Scatter data={fitData} shape={(props: any) => <circle cx={props.cx} cy={props.cy} r={7} fill={props.payload.fill} stroke="#fff" strokeWidth={2} />} /></ScatterChart></ResponsiveContainer></div><div className="quadrant-legend"><span><i className="dot teal" /> ready to try</span><span><i className="dot coral" /> build evidence</span><span><i className="dot ink" /> prepare first</span></div></section><section className="panel plan-panel span-12"><div className="panel-top"><div><div className="eyebrow">Your next four weeks</div><h2>Try something small next.</h2></div><span className="plan-number">04</span></div><div className="plan-grid">{[{ week: '01', title: 'Compare courses', body: 'Look at two Computer Science degree plans. Notice which subjects make you curious.', status: 'This week' }, { week: '02', title: 'Make a tiny project', body: 'Build a small data story or interactive page. Keep it rough and learn from it.', status: 'Next' }, { week: '03', title: 'Talk to a person', body: 'Ask a CS student or professional what their normal week really looks like.', status: 'Later' }, { week: '04', title: 'Write what you noticed', body: 'What gave you energy? What felt hard in a useful way? Add it to My progress.', status: 'Later' }].map((item) => <div className="plan-item" key={item.week}><span className="week-no">{item.week}</span><div><span className="rec-label">{item.status}</span><h3>{item.title}</h3><p>{item.body}</p></div><span className="plan-check">○</span></div>)}</div></section></div></div>
}

function Results({ profile }: { profile: Profile; savedMajors: string[]; toggleMajor: (name: string) => void }) {
  const result = profile.lastResult
  const scores = result?.domainScores || profile.scores
  const composite = result?.composite || profile.composite || Math.round(domains.reduce((total, domain) => total + scores[domain], 0) / domains.length)
  const confidence = result?.confidence || profile.confidence || 'demo snapshot'
  const ranked = [...domains].sort((a, b) => scores[b] - scores[a])
  const metricFor = (domain: Domain) => result?.domainMetrics[domain]
  const formatTime = (milliseconds: number | null | undefined) => milliseconds ? `${(milliseconds / 1000).toFixed(1)}s median` : 'Timing not recorded'
  const strongest = ranked.slice(0, 2).join(' and ')
  const lower = ranked[ranked.length - 1]
  return <div className="page results-page">
    <PageIntro eyebrow="Your results / Private report" title={<>See your results.<br /><em>Understand your profile.</em></>} body="This is a snapshot of how your answers compared across seven thinking areas today. It is a starting point for reflection, not a fixed label." action={<button className="button primary" onClick={() => window.print()}>Print my report <span>↗</span></button>} />
    <div className="result-disclaimer"><div className="disclaimer-mark">!</div><div><strong>Experimental IAQ Cognitive Profile / {composite}</strong><p>{result?.disclaimer || 'This demo result is provisional. It is not a clinical diagnosis or an officially normed IQ score.'}</p></div><Link to="/methodology">Read the method ↗</Link></div>
    <div className="result-grid results-top-grid"><section className="panel cognitive-panel span-8"><div className="result-score-head"><div><div className="eyebrow">Your profile score / 0–100</div><div className="result-score">{composite}<span>/100</span></div></div><div className="result-meta"><span className="confidence-badge">{confidence} confidence</span><span>{result ? new Date(result.completedAt).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : profile.lastAssessment}</span><span>{result?.assessmentVersion || 'IAQ-COG-0.3'}</span></div></div><div className="profile-distribution"><div className="distribution-scale"><span>0</span><span>50</span><span>100</span></div>{ranked.map((domain) => { const metric = metricFor(domain); return <div className="distribution-row" key={domain}><div className="distribution-label"><span className={`domain-swatch ${domainMeta[domain].tone}`} /><strong>{domain}</strong><b>{scores[domain]}</b></div><div className="distribution-track"><i className={domainMeta[domain].tone} style={{ width: `${scores[domain]}%` }} /><span className="distribution-average" style={{ left: `${composite}%` }} aria-hidden="true" /></div><div className="distribution-detail"><span>{metric?.correct ?? '—'} of {metric?.answered ?? '—'} correct</span><span>{metric?.relative || 'relative to your profile'}</span></div></div> })}</div><div className="result-caption"><span><i className="legend-dot cobalt" /> your profile today</span><span><i className="legend-line" /> your average</span></div></section><aside className="panel result-context"><div className="eyebrow">Read the shape</div><h2>What stands out</h2><p className="result-lede"><strong>{strongest}</strong> are your strongest relative signals in this attempt.</p><div className="result-observation"><span className="observation-mark teal">+</span><div><strong>Strengths to notice</strong><p>These areas came through more strongly than the rest of your profile.</p></div></div><div className="result-observation"><span className="observation-mark coral">→</span><div><strong>More evidence needed</strong><p>{lower} is your lowest relative signal today. Treat it as a question to explore, not a verdict.</p></div></div><div className="result-context-foot"><span>Distribution is within your profile.</span><strong>No population percentile shown.</strong></div></aside></div>
    <section className="result-evidence-strip"><div><span className="eyebrow">Questions answered</span><strong>{result ? `${result.answeredCount} / ${result.questionCount}` : 'Demo view'}</strong><span>balanced across seven areas</span></div><div><span className="eyebrow">Time limit</span><strong>{result ? `${Math.ceil(result.durationSeconds / 60)} minutes` : '35 minutes'}</strong><span>the test is time-limited</span></div><div><span className="eyebrow">How to read this</span><strong>Compare the bars</strong><span>not yourself with other people</span></div></section>
    <div className="result-grid result-secondary-grid"><section className="panel secondary-result-panel span-7"><div className="eyebrow">Next, when you are ready</div><h2>Explore what fits you.</h2><p>After your thinking profile, interests and real experiences can add useful context to possible directions. They do not change this result.</p><div className="secondary-actions"><Link className="button secondary" to="/compass">Explore directions <span>→</span></Link><Link className="text-button" to="/tracker">Check your progress ↗</Link></div></section><section className="panel timing-panel span-5"><div className="eyebrow">How timing affected this snapshot</div><h2>{result?.quality?.status === 'acceptable' ? 'Your session looked steady.' : 'Keep timing in context.'}</h2><p>{result?.quality?.warnings?.length ? `The session recorded ${result.quality.warnings.length} quality note${result.quality.warnings.length > 1 ? 's' : ''}. That does not silently change your score, but it is useful context for reading the bars.` : 'No timing warning was recorded. Faster is not automatically better; accuracy and concentration both matter.'}</p><div className="timing-note"><span className="notice-icon">i</span><span>{result ? `Median response times are shown per domain. ${formatTime(metricFor(ranked[0])?.medianResponseTimeMs)}` : 'Complete the timed assessment to see response-time context here.'}</span></div></section></div>
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

function Methodology() { return <div className="page legal-page"><PageIntro eyebrow="IAQ / Methodology" title={<>Useful now.<br /><em>Honest about limits.</em></>} body="IAQ V1.0 is designed as an early educational product. It is built to become more evidence-based through real pilots, not to simulate scientific certainty." /><div className="legal-grid"><section><div className="eyebrow">01 / What we measure</div><h2>Seven cognitive domains, one relative profile.</h2><p>We show how signals compare within your own profile. We do not show population percentiles, a fake bell curve, or a clinical IQ diagnosis.</p>{domains.map((domain, i) => <div className="method-row" key={domain}><span>0{i + 1}</span><strong>{domain}</strong><p>{domainMeta[domain].description}</p></div>)}</section><section className="legal-callout"><span className="notice-icon">i</span><h2>Content can be generated. Evidence cannot.</h2><p>AI may help draft candidates, distractors, or explanations. Real student responses are required to estimate difficulty, discrimination, fairness, and predictive value.</p><div className="method-steps"><span><b>01</b> reviewed families</span><span><b>02</b> deterministic variants</span><span><b>03</b> human review</span><span><b>04</b> real pilot data</span></div></section></div><div className="legal-footer"><Link to="/privacy">Read privacy model ↗</Link><Link to="/">Return to overview ↗</Link></div></div> }
function Privacy() { return <div className="page legal-page"><PageIntro eyebrow="IAQ / Privacy model" title={<>A profile should<br /><em>belong to you.</em></>} body="We design for minors, consent, and the minimum useful data. Demo mode keeps everything in this browser." /><div className="privacy-grid">{[{ title: 'Consent first', body: 'Assessment access requires a clear consent record and versioned notice. Guardian support is part of the production data model.' }, { title: 'Identity apart', body: 'Identity and research response data are separate concepts. Export and deletion flows are planned as first-class product capabilities.' }, { title: 'No surveillance', body: 'No camera, microphone, eye tracking, emotion detection, or secret behavioural inference is used.' }, { title: 'Human context', body: 'Reports explain signals and uncertainty. They do not diagnose, decide a student’s future, or rank students publicly.' }].map((item, i) => <div className="privacy-card" key={item.title}><span>0{i + 1}</span><h2>{item.title}</h2><p>{item.body}</p></div>)}</div><div className="notice-bar"><span className="notice-icon">!</span><span><strong>Demo mode note.</strong> This local preview uses seeded example data. Configure a production database, authentication provider, encryption, and retention policy before collecting real student responses.</span></div></div> }

export default App
