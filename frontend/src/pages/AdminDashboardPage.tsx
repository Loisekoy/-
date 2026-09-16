import { Activity, CalendarPlus, Dumbbell, UsersRound } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError, adminRequest } from '../api/client'
import type { AdminDashboard } from '../api/types'
import { ErrorNotice } from '../components/ErrorNotice'
import { LoadingScreen } from '../components/LoadingScreen'
import { parseApiDate } from '../lib/datetime'
import { clearAdminToken, getAdminToken } from '../lib/storage'

function MetricCard({
  label,
  value,
  suffix,
  icon: Icon,
}: {
  label: string
  value: string | number
  suffix?: string
  icon: LucideIcon
}) {
  return (
    <article className="admin-metric-card">
      <span>
        <Icon size={19} />
        {label}
      </span>
      <strong>
        {value}
        {suffix ? <small>{suffix}</small> : null}
      </strong>
    </article>
  )
}

export default function AdminDashboardPage() {
  const navigate = useNavigate()
  const [dashboard, setDashboard] = useState<AdminDashboard | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!getAdminToken()) {
      navigate('/admin/login', { replace: true })
      return
    }
    let active = true
    adminRequest<AdminDashboard>('/admin/dashboard')
      .then((payload) => {
        if (active) setDashboard(payload)
      })
      .catch((reason) => {
        if (!active) return
        if (reason instanceof ApiError && reason.status === 401) {
          clearAdminToken()
          navigate('/admin/login', { replace: true })
          return
        }
        setError(reason instanceof Error ? reason.message : '無法載入後台 Dashboard。')
      })
    return () => {
      active = false
    }
  }, [navigate])

  if (!dashboard && !error) return <LoadingScreen label="正在載入 Admin Dashboard" />
  if (!dashboard) return <main className="page admin-page"><ErrorNotice message={error} /></main>

  return (
    <main className="page admin-page">
      <header className="page-heading admin-heading">
        <div>
          <h1>Admin Dashboard</h1>
          <p>管理者後台可直接查看雲端資料庫中的使用者、課表、訓練與統計資料。</p>
        </div>
        <Link className="button button--secondary" to="/database">
          查看 DB Schema
        </Link>
      </header>

      <section className="admin-metric-grid" aria-label="後台核心統計">
        <MetricCard label="Total Users" value={dashboard.total_users} icon={UsersRound} />
        <MetricCard label="New Users Today" value={dashboard.new_users_today} icon={CalendarPlus} />
        <MetricCard label="Total Workouts" value={dashboard.total_workouts} icon={Dumbbell} />
        <MetricCard
          label="Training Volume"
          value={dashboard.total_training_volume.toLocaleString()}
          suffix="kg"
          icon={Activity}
        />
      </section>

      <section className="admin-dashboard-grid">
        <article className="admin-card">
          <div className="section-heading">
            <h2>Database Summary</h2>
            <Link to="/admin/statistics">查看統計 →</Link>
          </div>
          <dl className="admin-definition-list">
            <div>
              <dt>Total Workout Plans</dt>
              <dd>{dashboard.total_workout_plans}</dd>
            </div>
            <div>
              <dt>Average Age</dt>
              <dd>{dashboard.average_age?.toFixed(1) ?? '—'}</dd>
            </div>
            <div>
              <dt>Average Training Days</dt>
              <dd>{dashboard.average_training_days?.toFixed(1) ?? '—'} / week</dd>
            </div>
          </dl>
        </article>

        <article className="admin-card admin-card--wide">
          <div className="section-heading">
            <h2>Recent Users</h2>
            <Link to="/admin/users">管理 Users →</Link>
          </div>
          <div className="admin-table" role="table" aria-label="最近建立的使用者">
            <div className="admin-table__header" role="row">
              <span>Name</span>
              <span>Goal</span>
              <span>Experience</span>
              <span>Joined</span>
            </div>
            {dashboard.recent_users.length ? dashboard.recent_users.map((user) => (
              <Link
                className="admin-table__row"
                role="row"
                key={user.user_id}
                to={`/admin/users/${user.user_id}`}
              >
                <strong>{user.name}</strong>
                <span>{user.goal}</span>
                <span>{user.experience}</span>
                <time>{parseApiDate(user.joined).toLocaleDateString('zh-TW')}</time>
              </Link>
            )) : (
              <p className="admin-empty">目前還沒有使用者資料。</p>
            )}
          </div>
        </article>
      </section>
    </main>
  )
}
