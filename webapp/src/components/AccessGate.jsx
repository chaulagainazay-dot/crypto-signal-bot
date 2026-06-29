import { useState, useEffect } from 'react'

const API = '' // same origin

function getWebAppUser() {
  try {
    const tg = window.Telegram?.WebApp
    if (tg?.initDataUnsafe?.user) return tg.initDataUnsafe.user
  } catch {}
  return null
}

export default function AccessGate({ onGranted }) {
  const [status,   setStatus]   = useState('checking') // checking | approved | pending | denied | form
  const [reason,   setReason]   = useState('')
  const [sending,  setSending]  = useState(false)
  const [error,    setError]    = useState('')

  const user = getWebAppUser()
  const userId = user?.id ? String(user.id) : null

  useEffect(() => {
    if (!userId) {
      // No Telegram context — likely running in browser outside Telegram
      // Allow access in dev/preview mode
      if (import.meta.env.DEV) { onGranted(); return }
      setStatus('no_telegram')
      return
    }
    checkAccess()
  }, [userId])

  async function checkAccess() {
    setStatus('checking')
    try {
      const r = await fetch(`${API}/api/check?user_id=${userId}`)
      const d = await r.json()
      if (d.approved) { onGranted(); return }
      setStatus(d.pending ? 'pending' : 'form')
    } catch {
      // Network error — allow access rather than blocking everyone
      onGranted()
    }
  }

  async function submitRequest() {
    if (!reason.trim()) { setError('Please write a short reason.'); return }
    setSending(true); setError('')
    try {
      const r = await fetch(`${API}/api/register`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          user_id:    userId,
          username:   user?.username    || '',
          first_name: user?.first_name  || '',
          reason,
        }),
      })
      const d = await r.json()
      if (d.ok) setStatus(d.status === 'already_approved' ? 'approved_now' : 'pending')
      else setError(d.error || 'Request failed. Try again.')
    } catch {
      setError('Network error. Please try again.')
    }
    setSending(false)
  }

  // ── Checking ──────────────────────────────────────────────────────────────
  if (status === 'checking') {
    return (
      <div style={centeredStyle}>
        <div style={{ fontSize: 40, marginBottom: 16 }}>🔐</div>
        <div style={{ color: '#A0A0A0', fontSize: 14 }}>Checking access…</div>
        <Spinner />
      </div>
    )
  }

  // ── No Telegram (opened outside app) ─────────────────────────────────────
  if (status === 'no_telegram') {
    return (
      <div style={centeredStyle}>
        <div style={{ fontSize: 40, marginBottom: 12 }}>📱</div>
        <h2 style={{ margin: '0 0 8px' }}>Open in Telegram</h2>
        <p style={{ color: '#808080', fontSize: 13, textAlign: 'center', padding: '0 24px' }}>
          This app is a Telegram Mini App. Please open it through the bot.
        </p>
      </div>
    )
  }

  // ── Pending ───────────────────────────────────────────────────────────────
  if (status === 'pending') {
    return (
      <div style={centeredStyle}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>⏳</div>
        <h2 style={{ margin: '0 0 8px' }}>Request Pending</h2>
        <p style={{ color: '#808080', fontSize: 13, textAlign: 'center', padding: '0 32px', lineHeight: 1.7 }}>
          Your access request has been sent to the admin.<br />
          You'll be notified here when approved.
        </p>
        <button onClick={checkAccess} className="btn" style={{ marginTop: 24, width: 180 }}>
          🔄 Check Again
        </button>
      </div>
    )
  }

  // ── Approved in this session ──────────────────────────────────────────────
  if (status === 'approved_now') {
    return (
      <div style={centeredStyle}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>✅</div>
        <h2 style={{ margin: '0 0 8px' }}>Already Approved!</h2>
        <button onClick={onGranted} className="btn" style={{ marginTop: 16 }}>
          Open App →
        </button>
      </div>
    )
  }

  // ── Registration form ─────────────────────────────────────────────────────
  return (
    <div style={{ ...centeredStyle, justifyContent: 'flex-start', paddingTop: 60 }}>
      {/* Logo */}
      <div style={{ fontSize: 52, marginBottom: 8 }}>📊</div>
      <h2 style={{ margin: '0 0 4px', fontSize: 22 }}>HCG Trading App</h2>
      <p style={{ color: '#606060', fontSize: 12, marginBottom: 32 }}>Private Access</p>

      {/* Card */}
      <div style={{
        width: '100%', maxWidth: 340,
        background: '#141414', borderRadius: 16,
        padding: '24px 20px', border: '1px solid #2A2A2A',
      }}>
        <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 6 }}>Request Access</div>
        <p style={{ color: '#808080', fontSize: 12, marginBottom: 20, lineHeight: 1.6 }}>
          This app is private. Tell the admin who you are and why you want access.
        </p>

        {/* User info (read-only) */}
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16,
            padding: '10px 12px', background: '#1A1A1A', borderRadius: 10 }}>
            <div style={{ width: 36, height: 36, borderRadius: '50%', background: '#F7931A33',
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>
              {(user.first_name || '?')[0].toUpperCase()}
            </div>
            <div>
              <div style={{ fontWeight: 600, fontSize: 13 }}>
                {user.first_name}{user.last_name ? ' ' + user.last_name : ''}
              </div>
              {user.username && (
                <div style={{ color: '#606060', fontSize: 11 }}>@{user.username}</div>
              )}
            </div>
            <div style={{ marginLeft: 'auto', color: '#404040', fontSize: 10 }}>ID: {userId}</div>
          </div>
        )}

        <textarea
          value={reason}
          onChange={e => setReason(e.target.value)}
          placeholder="Why do you want to join? (e.g. I'm from the HCG group, member since 2023)"
          rows={3}
          style={{
            width: '100%', background: '#0D0D0D', border: '1px solid #2A2A2A',
            borderRadius: 10, padding: '12px', color: '#E0E0E0', fontSize: 13,
            resize: 'none', boxSizing: 'border-box', lineHeight: 1.6,
          }}
        />

        {error && (
          <div style={{ color: '#FF3D57', fontSize: 12, marginTop: 6 }}>{error}</div>
        )}

        <button
          className="btn"
          onClick={submitRequest}
          disabled={sending}
          style={{ marginTop: 14, width: '100%', opacity: sending ? 0.6 : 1 }}
        >
          {sending ? 'Sending…' : '📩 Send Request'}
        </button>
      </div>

      <p style={{ color: '#404040', fontSize: 11, marginTop: 20, textAlign: 'center', padding: '0 32px' }}>
        The admin will approve or deny your request. You'll receive a Telegram notification.
      </p>
    </div>
  )
}

const centeredStyle = {
  display:        'flex',
  flexDirection:  'column',
  alignItems:     'center',
  justifyContent: 'center',
  height:         '100dvh',
  padding:        '0 20px',
  background:     'var(--bg)',
}

function Spinner() {
  return (
    <div style={{
      width: 24, height: 24, marginTop: 16,
      border: '3px solid #2A2A2A',
      borderTop: '3px solid #F7931A',
      borderRadius: '50%',
      animation: 'spin 0.8s linear infinite',
    }} />
  )
}
