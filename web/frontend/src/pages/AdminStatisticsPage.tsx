import { BarChart3, Dumbbell, UsersRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { ApiError, adminRequest } from '../api/client'
import type { AdminStatistics, MetricPoint } from '../api/types'
import { ErrorNotice } from '../components/ErrorNotice'
import { LoadingScreen } from '../components/LoadingScreen'
import { clearAdminToken, getAdminToken } from '../lib/storage'

const COLORS = ['#1769ff', '#c7ff38', '#07182d', '#95cf00', '#6d7888', '#ffb020', '#d92d20', '#5e5ce6']

function EmptyChart() {
  return <div className="admin-empty-chart">目前還沒有足夠資料產生圖表。</div>
}

function BarPanel({ title, subtitle, data }: { title: string; subtitle: string; data: MetricPoint[] }) {
  return (
    <article className="chart-panel admin-chart-panel">
      <h2>{title}</h2>
      <p>{subtitle}</p>
      <div className="chart-container">
        {data.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 12, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="label" tickLine={false} axisLine={false} />
              <YAxis tickLine={false} axisLine={false} width={44} />
              <Tooltip />
              <Bar dataKey="value" fill="#1769ff" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : <EmptyChart />}
      </div>
    </article>
  )
}

function PiePanel({ title, subtitle, data }: { title: string; subtitle: string; data: MetricPoint[] }) {
  return (
    <article className="chart-panel admin-chart-panel">
      <h2>{title}</h2>
      <p>{subtitle}</p>
      <div className="chart-container">
        {data.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Tooltip />
              <Pie data={data} dataKey="value" nameKey="label" outerRadius={105} label>
                {data.map((item, index) => (
                  <Cell key={item.label} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        ) : <EmptyChart />}
      </div>
    </article>
  )
}

export default function AdminStatisticsPage() {
  const navigate = useNavigate()
  const [statistics, setStatistics] = useState<AdminStatistics | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!getAdminToken()) {
      navigate('/admin/login', { replace: true })
      return
    }
    let active = true
    adminRequest<AdminStatistics>('/admin/statistics')
      .then((payload) => {
        if (active) setStatistics(payload)
      })
      .catch((reason) => {
        if (!active) return
        if (reason instanceof ApiError && reason.status === 401) {
          clearAdminToken()
          navigate('/admin/login', { replace: true })
          return
        }
        setError(reason instanceof Error ? reason.message : '無法載入統計資料。')
      })
    return () => {
      active = false
    }
  }, [navigate])

  if (!statistics && !error) return <LoadingScreen label="正在載入 Admin Statistics" />
  if (!statistics) return <main className="page admin-page"><ErrorNotice message={error} /></main>

  return (
    <main className="page admin-page">
      <header className="page-heading admin-heading">
        <div>
          <h1>Statistics</h1>
          <p>所有圖表都由資料庫查詢產生，展示 GROUP BY、COUNT、SUM、AVG 與 ORDER BY。</p>
        </div>
      </header>
      {error ? <ErrorNotice message={error} /> : null}

      <section className="admin-metric-grid">
        <article className="admin-metric-card">
          <span><UsersRound size={19} />Total Users</span>
          <strong>{statistics.total_users}</strong>
        </article>
        <article className="admin-metric-card">
          <span><Dumbbell size={19} />Workout Sessions</span>
          <strong>{statistics.total_workout_sessions}</strong>
        </article>
        <article className="admin-metric-card">
          <span><BarChart3 size={19} />Total Volume</span>
          <strong>{statistics.total_training_volume.toLocaleString()}<small>kg</small></strong>
        </article>
        <article className="admin-metric-card">
          <span>Average Training Days</span>
          <strong>{statistics.average_training_days_per_week?.toFixed(1) ?? '—'}<small>/ week</small></strong>
        </article>
      </section>

      <section className="admin-chart-grid">
        <PiePanel title="Users by Training Goal" subtitle="GROUP BY training_goals.goal_name" data={statistics.users_by_training_goal} />
        <BarPanel title="Users by Experience" subtitle="GROUP BY users.training_experience" data={statistics.users_by_experience_level} />
        <BarPanel title="Most Selected Body Parts" subtitle="JOIN user_body_parts + body_parts" data={statistics.most_selected_body_parts} />
        <BarPanel title="Most Popular Exercises" subtitle="JOIN workout_sets + exercises" data={statistics.most_popular_exercises} />
      </section>
    </main>
  )
}
