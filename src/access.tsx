import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { beginCheckout, createOrder, devLogin, getCurrentUser, getOrderStatus, listProducts, logout, requestOtp, settleMockPayment, verifyOtp, type AccessUser, type Order, type Product } from './api'

const demoAccounts = [
  { id: 'demo-student', label: 'Student preview', detail: 'Ari · assessment access' },
  { id: 'demo-guardian', label: 'Guardian preview', detail: 'Sari · purchase for a student' },
  { id: 'demo-counselor', label: 'Counselor preview', detail: 'Maya · assigned students only' },
  { id: 'demo-school-admin', label: 'School admin preview', detail: 'Bima · seats and billing' },
  { id: 'demo-admin', label: 'Platform admin preview', detail: 'IAQ admin · MFA-ready' },
]

function safeReturnTo(value: string | null) {
  return value && value.startsWith('/') && !value.startsWith('//') ? value : '/'
}

export function AuthLogin() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [selected, setSelected] = useState('demo-student')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [otpSent, setOtpSent] = useState(false)
  const login = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await devLogin(selected)
      navigate(safeReturnTo(searchParams.get('returnTo')))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Sign in is unavailable right now.')
    } finally { setBusy(false) }
  }
  const sendCode = async () => { if (!email.trim()) { setError('Enter your email first.'); return } setBusy(true); setError(''); try { await requestOtp(email.trim()); setOtpSent(true) } catch (reason) { setError(reason instanceof Error ? reason.message : 'We could not send a code.') } finally { setBusy(false) } }
  const verifyCode = async (event: FormEvent) => { event.preventDefault(); setBusy(true); setError(''); try { await verifyOtp(email.trim(), code.trim()); navigate(safeReturnTo(searchParams.get('returnTo'))) } catch (reason) { setError(reason instanceof Error ? reason.message : 'That code could not be verified.') } finally { setBusy(false) } }
  return <div className="access-page"><div className="access-frame"><Link className="access-brand" to="/welcome">IAQ<span>.</span></Link><div className="access-grid"><section className="access-intro"><div className="eyebrow">Sign in / IAQ workspace</div><h1>Keep your profile<br /><em>in your hands.</em></h1><p>Sign in to start a test, read your results, save directions, or continue where you left off.</p><div className="access-note"><strong>Staff accounts are invitation-only.</strong><span>Counselor, school, reviewer, and platform access is never created through public signup.</span></div></section><section className="access-card"><h2>Continue to IAQ</h2><p className="muted">Local development mode is enabled. Choose a seeded account to preview each protected workflow.</p><button className="oauth-button" type="button" disabled><span className="oauth-mark">G</span> Continue with Google <small>setup required</small></button><div className="form-divider"><span>or use a development account</span></div><form onSubmit={login}><label>Account<select value={selected} onChange={(event) => setSelected(event.target.value)}>{demoAccounts.map((account) => <option key={account.id} value={account.id}>{account.label} — {account.detail}</option>)}</select></label><button className="button primary full" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'} <span>→</span></button>{error && <p className="form-error" role="alert">{error}</p>}</form><div className="form-divider"><span>Email code fallback</span></div>{!otpSent ? <div className="otp-form"><label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" /></label><button className="button ghost" type="button" onClick={sendCode} disabled={busy}>Send me a code <span>→</span></button></div> : <form className="otp-form" onSubmit={verifyCode}><label>Six-digit code<input inputMode="numeric" value={code} onChange={(event) => setCode(event.target.value)} placeholder="123456" maxLength={6} /></label><button className="button secondary" disabled={busy}>Verify and continue <span>→</span></button><small className="muted">Development code: 123456</small></form>}<small className="legal-copy">By continuing, you agree to the draft <Link to="/privacy">privacy model</Link>. Production auth uses Supabase Auth with PKCE once configured.</small></section></div></div></div>
}

export function AuthCallback() {
  return <div className="access-page"><div className="access-card standalone"><div className="eyebrow">Authentication callback</div><h1>One more step.</h1><p>Connect Supabase Auth to finish Google or email sign-in. The local preview uses the development sign-in screen.</p><Link className="button primary" to="/auth/login">Back to sign in <span>→</span></Link></div></div>
}

export function AccountSettings() {
  const [user, setUser] = useState<AccessUser | null>(null)
  const [signedOut, setSignedOut] = useState(false)
  useEffect(() => { getCurrentUser().then(setUser).catch(() => undefined) }, [])
  if (signedOut) return <div className="page access-settings"><div className="panel"><div className="eyebrow">Signed out</div><h1>Your session is closed.</h1><Link className="button primary" to="/auth/login">Sign in again <span>→</span></Link></div></div>
  return <div className="page access-settings"><div className="compact-hero"><div><div className="eyebrow">Account / security boundary</div><h1>Your account.<br /><em>Your choices.</em></h1><p>Identity, permissions, purchases, and assessment evidence stay separate so access can be reviewed and withdrawn safely.</p></div><button className="button ghost" onClick={async () => { await logout(); setSignedOut(true) }}>Sign out</button></div>{user && <div className="settings-grid"><section className="panel"><div className="eyebrow">Profile</div><h2>{user.display_name}</h2><p>{user.email}</p><dl className="settings-list"><div><dt>Workspace</dt><dd>{user.roles.join(' · ')}</dd></div><div><dt>Account status</dt><dd>{user.account_status}</dd></div><div><dt>Staff MFA</dt><dd>{user.mfa_verified ? 'Verified in development' : 'Required before access'}</dd></div></dl></section><section className="panel"><div className="eyebrow">Next places</div><div className="settings-links"><Link to="/pricing"><strong>Plan & billing</strong><span>View products and orders →</span></Link><Link to="/privacy"><strong>Privacy</strong><span>Read the IAQ data model →</span></Link><Link to="/methodology"><strong>Help & methodology</strong><span>Understand the assessment →</span></Link></div></section></div>}</div>
}

function formatIDR(amount: number) { return amount === 0 ? 'Free' : new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(amount) }

export function Pricing() {
  const [products, setProducts] = useState<Product[]>([])
  const [error, setError] = useState('')
  useEffect(() => { listProducts().then(setProducts).catch((reason) => setError(reason instanceof Error ? reason.message : 'Products could not load.')) }, [])
  return <div className="page commerce-page"><div className="compact-hero"><div><div className="eyebrow">IAQ / plans and access</div><h1>Choose what you<br /><em>want to explore.</em></h1><p>Start with a free preview or unlock the complete report. Prices come from the backend, not from the browser.</p></div><Link className="button ghost" to="/auth/login">Switch account <span>↗</span></Link></div><div className="commerce-note"><span className="notice-icon">i</span><span>Payments are in sandbox mode. A payment status is only confirmed after the server verifies it and creates an entitlement.</span></div>{error && <div className="form-error">{error}</div>}<div className="product-grid">{products.map((product) => <article className={`product-card ${product.id === 'iaq-complete' ? 'featured' : ''}`} key={product.id}><div className="eyebrow">{product.id === 'iaq-complete' ? 'Most complete' : 'Start here'}</div><h2>{product.name}</h2><p>{product.description}</p><strong className="product-price">{formatIDR(product.amount_minor)}</strong><Link className="button primary full" to={`/checkout/${product.id}`}>{product.amount_minor === 0 ? 'Start free' : 'See checkout'} <span>→</span></Link><small>One-time access · IDR · no subscription</small></article>)}</div></div>
}

export function Checkout() {
  const { productId = '' } = useParams()
  const navigate = useNavigate()
  const [product, setProduct] = useState<Product | null>(null)
  const [beneficiary, setBeneficiary] = useState('')
  const [accepted, setAccepted] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { listProducts().then((items) => setProduct(items.find((item) => item.id === productId) || null)).catch(() => setError('Product could not load.')) }, [productId])
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!accepted) { setError('Please accept the IAQ terms and refund policy first.'); return }
    setBusy(true); setError('')
    try {
      const order = await createOrder(productId, beneficiary.trim() || undefined)
      navigate(`/checkout/${order.id}/pay`)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Checkout could not start.') } finally { setBusy(false) }
  }
  if (!product) return <div className="page commerce-page"><div className="panel"><div className="eyebrow">Checkout</div><h1>{error || 'Loading product…'}</h1><Link to="/pricing" className="text-button">Back to pricing ↗</Link></div></div>
  return <div className="page commerce-page"><div className="compact-hero"><div><div className="eyebrow">Checkout / one-time access</div><h1>Confirm your<br /><em>IAQ access.</em></h1><p>We calculate the authoritative total on the server. The beneficiary receives the entitlement after payment verification.</p></div><Link className="button ghost" to="/pricing">Back to plans <span>←</span></Link></div><div className="checkout-grid"><form className="panel checkout-form" onSubmit={submit}><div className="eyebrow">Order details</div><h2>{product.name}</h2><label>Beneficiary user ID <input value={beneficiary} onChange={(event) => setBeneficiary(event.target.value)} placeholder="Leave blank for yourself" /><small>Guardians can use <code>demo-student</code> in development. Production checks the verified relationship server-side.</small></label><label className="check-row"><input type="checkbox" checked={accepted} onChange={(event) => setAccepted(event.target.checked)} /><span>I accept the IAQ terms, draft refund policy, and experimental-result notice.</span></label><button className="button primary" disabled={busy}>{busy ? 'Creating order…' : 'Continue to payment'} <span>→</span></button>{error && <p className="form-error" role="alert">{error}</p>}</form><aside className="panel order-summary"><div className="eyebrow">Order summary</div><div className="summary-line"><span>{product.name}</span><strong>{formatIDR(product.amount_minor)}</strong></div><div className="summary-line"><span>Discount</span><span>—</span></div><div className="summary-line"><span>Tax</span><span>—</span></div><div className="summary-total"><span>Total</span><strong>{formatIDR(product.amount_minor)}</strong></div><small>Currency: IDR · provider: sandbox/mock</small></aside></div></div>
}

export function PaymentPage() {
  const { orderId = '' } = useParams()
  const navigate = useNavigate()
  const [order, setOrder] = useState<Order | null>(null)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState('')
  const load = async () => { try { const status = await getOrderStatus(orderId); setOrder(status.order); if (status.order.status === 'fulfilled') setMessage('Access is active. The server created the entitlement.') } catch (reason) { setError(reason instanceof Error ? reason.message : 'Payment status could not load.') } finally { setBusy(false) } }
  useEffect(() => { beginCheckout(orderId).then((result) => { setOrder(result.order); setMessage(result.message) }).catch((reason) => setError(reason instanceof Error ? reason.message : 'Checkout could not load.')).finally(() => setBusy(false)) }, [orderId])
  const settle = async () => { setBusy(true); setError(''); try { await settleMockPayment(orderId); await load() } catch (reason) { setError(reason instanceof Error ? reason.message : 'Sandbox payment failed.') } finally { setBusy(false) } }
  if (busy && !order) return <div className="page commerce-page"><div className="panel loading-card"><div className="eyebrow">Hosted checkout</div><h1>Preparing payment…</h1></div></div>
  return <div className="page commerce-page"><div className="compact-hero"><div><div className="eyebrow">Payment / {order?.order_number || orderId.slice(0, 8)}</div><h1>{order?.status === 'fulfilled' ? <>You’re ready<br /><em>to begin.</em></> : <>Payment is<br /><em>waiting for you.</em></>}</h1><p>{order?.status === 'fulfilled' ? 'Your entitlement is active. Start the assessment when you are ready.' : 'This local checkout simulates a hosted Midtrans flow. The success button below sends a verified server-side sandbox event.'}</p></div><span className={`payment-status ${order?.status}`}>{order?.status || 'pending'}</span></div><div className="payment-grid"><section className="panel"><div className="eyebrow">Server-confirmed state</div><h2>{message || 'Payment received. We are confirming it with the payment provider.'}</h2><p>Browser redirects never grant access by themselves. IAQ waits for a verified provider event before creating the entitlement.</p>{order?.status === 'fulfilled' ? <button className="button primary" onClick={() => navigate('/assess')}>Start test <span>→</span></button> : <button className="button primary" onClick={settle} disabled={busy}>Complete sandbox payment <span>→</span></button>}{error && <p className="form-error" role="alert">{error}</p>}</section><aside className="panel order-summary"><div className="eyebrow">Order</div><div className="summary-line"><span>Product</span><strong>{order?.product_snapshot?.name}</strong></div><div className="summary-line"><span>Total</span><strong>{order ? formatIDR(order.total_minor) : '—'}</strong></div><div className="summary-line"><span>Access</span><span>{order?.status === 'fulfilled' ? 'Granted' : 'Not yet granted'}</span></div><Link to="/app/billing" className="text-button">View billing history ↗</Link></aside></div></div>
}

export function Billing() {
  const [orders, setOrders] = useState<Order[]>([])
  useEffect(() => { fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'}/me/orders`, { headers: { 'X-IAQ-Session': localStorage.getItem('iaq-session-token') || '' } }).then((response) => response.json()).then((body) => setOrders(body.orders || [])).catch(() => undefined) }, [])
  return <div className="page commerce-page"><div className="compact-hero"><div><div className="eyebrow">Account / billing</div><h1>See your<br /><em>access history.</em></h1><p>Paid, pending, expired, and fulfilled states are kept distinct.</p></div><Link className="button primary" to="/pricing">View plans <span>→</span></Link></div><section className="panel billing-table"><div className="eyebrow">Orders</div>{orders.length ? orders.map((order) => <div className="billing-row" key={order.id}><div><strong>{order.product_snapshot?.name || order.product_id}</strong><span>{order.order_number}</span></div><span>{formatIDR(order.total_minor)}</span><b className={`payment-status ${order.status}`}>{order.status}</b><Link to={`/checkout/${order.id}/pay`} className="text-button">Open ↗</Link></div>) : <div className="empty-state"><h2>No orders yet.</h2><p>When you choose a product, the server will keep the order and access trail here.</p><Link to="/pricing" className="button secondary">See plans <span>→</span></Link></div>}</section></div>
}
