import { KeyRound, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiRequest } from '../api/client'
import type { AdminLoginResponse } from '../api/types'
import { ErrorNotice } from '../components/ErrorNotice'
import { getAdminToken, saveAdminToken } from '../lib/storage'

export default function AdminLoginPage() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (getAdminToken()) navigate('/admin', { replace: true })
  }, [navigate])

  async function submitLogin(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const response = await apiRequest<AdminLoginResponse>('/admin/login', {
        method: 'POST',
        body: JSON.stringify({ username: username.trim(), password }),
      })
      saveAdminToken(response.access_token)
      navigate('/admin')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '無法登入管理後台。')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="admin-login-page">
      <section className="admin-login-card">
        <div className="admin-login-card__badge">
          <ShieldCheck size={22} />
          Admin Backend
        </div>
        <h1>管理者登入</h1>
        <p>
          這裡是資料庫系統後台。公開使用者網站不需要登入；只有管理者可以查看所有使用者資料、
          統計與 Exercise Database。
        </p>
        {error ? <ErrorNotice message={error} /> : null}
        <form onSubmit={submitLogin} className="admin-login-form">
          <label className="field">
            <span>Admin Username</span>
            <input
              autoComplete="username"
              required
              minLength={3}
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            />
          </label>
          <label className="field">
            <span>Admin Password</span>
            <input
              autoComplete="current-password"
              required
              minLength={8}
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="由 ADMIN_BOOTSTRAP_PASSWORD 設定"
            />
          </label>
          <button className="button button--primary button--large" type="submit" disabled={busy}>
            <KeyRound size={19} />
            {busy ? '登入中…' : '登入後台'}
          </button>
        </form>
        <Link className="admin-login-card__back" to="/">
          回到公開網站
        </Link>
      </section>
    </main>
  )
}
