import { Activity, BarChart3, CalendarDays, Dumbbell, Scale, Target } from 'lucide-react'
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
import type { DashboardData, Profile, WorkoutPlan } from '../api/types'
import { ErrorNotice } from '../components/ErrorNotice'
import { LoadingScreen } from '../components/LoadingScreen'
import { parseApiDate } from '../lib/datetime'
import { getUserId } from '../lib/storage'

export default function DashboardPage() {
  const userId = getUserId()
  const [days, setDays] = useState(28)
  const [data, setData] = useState<DashboardData | null>(null)
  const [profile, setProfile] = useState<Profile | null>(null)
  const [plan, setPlan] = useState<WorkoutPlan | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!userId) return
    let active = true
    Promise.all([
      apiRequest<DashboardData>(`/users/${userId}/dashboard?days=${days}`),
      apiRequest<Profile>(`/users/${userId}`),
      apiRequest<WorkoutPlan>(`/users/${userId}/plans/active`).catch(() => null),
    ])
      .then(([dashboardPayload, profilePayload, planPayload]) => {
        if (!active) return
        setData(dashboardPayload)
        setProfile(profilePayload)
        setPlan(planPayload)
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message)
      })
    return () => {
      active = false
    }
  }, [days, userId])

  if (!userId) return <main className="empty-page"><h1>尚未建立健身資料</h1><Link className="button button--primary" to="/onboarding">開始建立</Link></main>
  if ((!data || !profile) && !error) return <LoadingScreen label="正在計算 Dashboard" />
  if (!data || !profile) return <main className="page"><ErrorNotice message={error} /></main>

  return (
    <main className="page dashboard-page">
      <header className="page-heading dashboard-heading">
        <div><h1>Dashboard</h1><p>掌握訓練進度，持續成為更好的自己。</p></div>
        <label className="range-select"><span>統計期間</span><select value={days} onChange={(event) => setDays(Number(event.target.value))}><option value="7">最近 1 週</option><option value="28">最近 4 週</option><option value="90">最近 3 個月</option><option value="180">最近 6 個月</option></select></label>
      </header>
      {error ? <ErrorNotice message={error} /> : null}

      <section className="dashboard-profile-band" aria-label="使用者與目前課表摘要">
        <div className="profile-summary">
          <span>目前使用者</span>
          <strong>{profile.name}</strong>
          <small>{profile.training_experience}・{profile.training_days_per_week} days/week・{profile.training_duration_minutes} minutes</small>
        </div>
        <div className="profile-summary">
          <span><Target size={18} />Training Goal</span>
          <strong>{profile.training_goal.goal_name}</strong>
          <small>{profile.training_goal.description ?? profile.training_goal.goal_code}</small>
        </div>
        <div className="profile-summary profile-summary--wide">
          <span>Preferred Body Parts</span>
          <div className="body-part-chips">
            {profile.preferred_body_parts.map((part) => (
              <small key={part.body_part_id}>{part.name_en} {part.name_zh}</small>
            ))}
          </div>
        </div>
        <div className="profile-summary profile-summary--wide">
          <span><CalendarDays size={18} />Current Workout Plan</span>
          {plan ? (
            <>
              <strong>{plan.plan_name}</strong>
              <small>{plan.days.length} days・{plan.training_duration_minutes} minutes・{plan.algorithm_version}</small>
            </>
          ) : (
            <>
              <strong>尚未產生課表</strong>
              <Link to="/plan">前往產生 →</Link>
            </>
          )}
        </div>
      </section>

      <section className="metric-strip" aria-label="核心統計">
        <div><span><Dumbbell size={20} />本週訓練</span><strong>{data.this_week_workouts}<small>次</small></strong></div>
        <div><span><Activity size={20} />總訓練次數</span><strong>{data.total_completed_workouts}<small>次</small></strong></div>
        <div><span><BarChart3 size={20} />Total Volume</span><strong>{data.total_training_volume_kg.toLocaleString()}<small>kg</small></strong></div>
        <div><span><Scale size={20} />最新體重</span><strong>{data.latest_weight_kg?.toFixed(1) ?? '—'}<small>kg</small></strong>{data.weight_change_kg !== null ? <em>{data.weight_change_kg > 0 ? '+' : ''}{data.weight_change_kg.toFixed(1)} kg</em> : null}</div>
      </section>

      <section className="metric-strip metric-strip--secondary" aria-label="統計期間細節">
        <div><span>期間訓練</span><strong>{data.completed_workouts}<small>次</small></strong></div>
        <div><span>期間工作組</span><strong>{data.working_sets}<small>組</small></strong></div>
        <div><span>期間 Volume</span><strong>{data.training_volume_kg.toLocaleString()}<small>kg</small></strong></div>
        <div><span>最常使用</span><strong>{data.most_used_exercise ?? '—'}</strong></div>
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
