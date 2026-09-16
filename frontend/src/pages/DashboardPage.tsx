import { Activity, BarChart3, Dumbbell, Scale } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { apiRequest } from '../api/client'
import type { DashboardData } from '../api/types'
import { ErrorNotice } from '../components/ErrorNotice'
import { LoadingScreen } from '../components/LoadingScreen'
import { parseApiDate } from '../lib/datetime'
import { getUserId } from '../lib/storage'

export default function DashboardPage() {
  const userId = getUserId()
  const [days, setDays] = useState(28)
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!userId) return
    let active = true
    apiRequest<DashboardData>(`/users/${userId}/dashboard?days=${days}`)
      .then((payload) => {
        if (active) setData(payload)
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message)
      })
    return () => {
      active = false
    }
  }, [days, userId])

  if (!userId) return <main className="empty-page"><h1>尚未建立健身資料</h1><Link className="button button--primary" to="/onboarding">開始建立</Link></main>
  if (!data && !error) return <LoadingScreen label="正在計算 Dashboard" />
  if (!data) return <main className="page"><ErrorNotice message={error} /></main>

  return (
    <main className="page dashboard-page">
      <header className="page-heading dashboard-heading">
        <div><h1>Dashboard</h1><p>掌握訓練進度，持續成為更好的自己。</p></div>
        <label className="range-select"><span>統計期間</span><select value={days} onChange={(event) => setDays(Number(event.target.value))}><option value="7">最近 1 週</option><option value="28">最近 4 週</option><option value="90">最近 3 個月</option><option value="180">最近 6 個月</option></select></label>
      </header>
      {error ? <ErrorNotice message={error} /> : null}

      <section className="metric-strip" aria-label="核心統計">
        <div><span><Dumbbell size={20} />本期訓練</span><strong>{data.completed_workouts}<small>次</small></strong></div>
        <div><span><Activity size={20} />本期工作組</span><strong>{data.working_sets}<small>組</small></strong></div>
        <div><span><BarChart3 size={20} />Training Volume</span><strong>{data.training_volume_kg.toLocaleString()}<small>kg</small></strong></div>
        <div><span><Scale size={20} />最新體重</span><strong>{data.latest_weight_kg?.toFixed(1) ?? '—'}<small>kg</small></strong>{data.weight_change_kg !== null ? <em>{data.weight_change_kg > 0 ? '+' : ''}{data.weight_change_kg.toFixed(1)} kg</em> : null}</div>
      </section>

      <section className="dashboard-charts">
        <div className="chart-panel">
          <h2>Training Volume</h2><p>Volume (kg)</p>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.weekly_volume} margin={{ left: 0, right: 12, top: 12, bottom: 0 }}>
                <CartesianGrid stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="label" tickLine={false} axisLine={false} />
                <YAxis tickLine={false} axisLine={false} width={56} />
                <Tooltip cursor={{ fill: '#f3f6fa' }} />
                <Bar dataKey="value" name="Volume" fill="#1769ff" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="chart-panel">
          <h2>Body Weight History</h2><p>Weight (kg)</p>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.weight_history} margin={{ left: 0, right: 16, top: 12, bottom: 0 }}>
                <CartesianGrid stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="label" tickLine={false} axisLine={false} />
                <YAxis domain={['dataMin - 2', 'dataMax + 2']} tickLine={false} axisLine={false} width={42} />
                <Tooltip />
                <Line type="monotone" dataKey="value" name="Weight" stroke="#1769ff" strokeWidth={2.5} dot={{ r: 4, fill: '#1769ff' }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section className="dashboard-lower">
        <div className="popular-metric"><span>最常訓練部位</span><strong>{data.most_trained_body_part ?? '—'}</strong></div>
        <div className="popular-metric"><span>最常使用 Exercise</span><strong>{data.most_used_exercise ?? '—'}</strong></div>
        <div className="recent-workouts">
          <div className="section-heading"><h2>最近訓練紀錄</h2><Link to="/history">查看全部 →</Link></div>
          {data.recent_workouts.map((workout) => (
            <div className="recent-workout-row" key={workout.session_id}><time>{parseApiDate(workout.started_at).toLocaleDateString('zh-TW')}</time><strong>{workout.session_name}</strong><span>{workout.set_count} 組</span><span>{workout.volume_kg.toLocaleString()} kg</span></div>
          ))}
        </div>
      </section>
    </main>
  )
}
