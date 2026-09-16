import { ArrowLeft, BrainCircuit, CalendarDays, Dumbbell, ListChecks, Scale, UserRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError, adminRequest } from '../api/client'
import type { AdminUserDetail } from '../api/types'
import { ErrorNotice } from '../components/ErrorNotice'
import { LoadingScreen } from '../components/LoadingScreen'
import { useI18n } from '../i18n'
import { parseApiDate } from '../lib/datetime'
import { getExerciseDisplayName, getExerciseImageSrc } from '../lib/exerciseGuidance'
import { clearAdminToken, getAdminToken } from '../lib/storage'

export default function AdminUserDetailPage() {
  const { userId } = useParams()
  const navigate = useNavigate()
  const { language } = useI18n()
  const [detail, setDetail] = useState<AdminUserDetail | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!getAdminToken()) {
      navigate('/admin/login', { replace: true })
      return
    }
    if (!userId) return
    let active = true
    adminRequest<AdminUserDetail>(`/admin/users/${userId}`)
      .then((payload) => {
        if (active) setDetail(payload)
      })
      .catch((reason) => {
        if (!active) return
        if (reason instanceof ApiError && reason.status === 401) {
          clearAdminToken()
          navigate('/admin/login', { replace: true })
          return
        }
        setError(reason instanceof Error ? reason.message : '無法載入使用者 detail。')
      })
    return () => {
      active = false
    }
  }, [navigate, userId])

  if (!userId) {
    return (
      <main className="page admin-page">
        <Link className="button button--secondary" to="/admin/users"><ArrowLeft size={17} />返回 Users</Link>
        <ErrorNotice message="缺少 user_id。" />
      </main>
    )
  }
  if (!detail && !error) return <LoadingScreen label="正在載入 User Detail" />
  if (!detail) {
    return (
      <main className="page admin-page">
        <Link className="button button--secondary" to="/admin/users"><ArrowLeft size={17} />返回 Users</Link>
        <ErrorNotice message={error} />
      </main>
    )
  }

  const { profile } = detail

  return (
    <main className="page admin-page">
      <header className="page-heading admin-heading">
        <div>
          <Link className="admin-back-link" to="/admin/users"><ArrowLeft size={17} />Users</Link>
          <h1>{profile.name}</h1>
          <p>User ID: {profile.user_id}</p>
        </div>
      </header>

      <section className="admin-detail-grid">
        <article className="admin-card">
          <div className="section-heading">
            <h2><UserRound size={20} />Profile</h2>
          </div>
          <dl className="admin-definition-list">
            <div><dt>Gender</dt><dd>{profile.gender ?? 'Not specified'}</dd></div>
            <div><dt>Age</dt><dd>{profile.age}</dd></div>
            <div><dt>Height</dt><dd>{profile.height_cm} cm</dd></div>
            <div><dt>Weight</dt><dd>{profile.latest_weight_kg} kg</dd></div>
            <div><dt>Experience</dt><dd>{profile.training_experience}</dd></div>
            <div><dt>Goal</dt><dd>{profile.training_goal.goal_name}</dd></div>
            <div><dt>Schedule</dt><dd>{profile.training_days_per_week} days / {profile.training_duration_minutes} min</dd></div>
            <div><dt>Created</dt><dd>{parseApiDate(profile.created_at).toLocaleString('zh-TW')}</dd></div>
          </dl>
          <div className="body-part-chips admin-chip-row">
            {profile.preferred_body_parts.map((part) => (
              <small key={part.body_part_id}>{part.name_en} {part.name_zh}</small>
            ))}
          </div>
        </article>

        <article className="admin-card">
          <div className="section-heading">
            <h2><Scale size={20} />Weight History</h2>
          </div>
          <div className="admin-mini-list">
            {detail.weight_history.map((record) => (
              <div key={record.body_record_id}>
                <time>{parseApiDate(record.recorded_on).toLocaleDateString('zh-TW')}</time>
                <strong>{record.weight_kg} kg</strong>
                <span>{record.notes ?? '—'}</span>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="admin-card">
        <div className="section-heading">
          <h2><CalendarDays size={20} />Workout Plans</h2>
          <p>{detail.workout_plans.length} plans</p>
        </div>
        <div className="admin-plan-list">
          {detail.workout_plans.length ? detail.workout_plans.map((plan) => (
            <article key={plan.plan_id}>
              <header>
                <div>
                  <h3>{plan.plan_name}</h3>
                  <p>{plan.status}・{parseApiDate(plan.generated_at).toLocaleString('zh-TW')}</p>
                </div>
              </header>
              <div className="admin-plan-days">
                {plan.days.map((day) => (
                  <div key={day.plan_day_id}>
                    <strong>Day {day.day_number} — {day.focus_summary}</strong>
                    <ul>
                      {day.exercises.map((item) => (
                        <li key={item.plan_exercise_id}>
                          <img src={getExerciseImageSrc(item.exercise)} alt="" />
                          <span>{getExerciseDisplayName(item.exercise, language)}</span>
                          <small>{item.target_sets} × {item.target_reps}・{item.rest_seconds}s</small>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </article>
          )) : <p className="admin-empty">這位使用者尚未產生課表。</p>}
        </div>
      </section>

      <section className="admin-card">
        <div className="section-heading">
          <h2><BrainCircuit size={20} />LLM Generations</h2>
          <p>{detail.llm_generations.length} records</p>
        </div>
        <div className="admin-table" role="table" aria-label="LLM generation records">
          <div className="admin-table__header" role="row">
            <span>Status</span>
            <span>Provider / Model</span>
            <span>Fallback</span>
            <span>Created</span>
            <span>Error</span>
          </div>
          {detail.llm_generations.length ? detail.llm_generations.map((generation) => (
            <div className="admin-table__row" role="row" key={generation.llm_generation_id}>
              <strong>{generation.status}</strong>
              <span>{generation.provider} / {generation.model}</span>
              <span>{generation.used_fallback ? 'Yes' : 'No'}</span>
              <time>{parseApiDate(generation.created_at).toLocaleString('zh-TW')}</time>
              <span>{generation.error_message ?? generation.response_summary ?? '—'}</span>
            </div>
          )) : <p className="admin-empty">尚未有 LLM 產生紀錄。</p>}
        </div>
      </section>

      <section className="admin-card">
        <div className="section-heading">
          <h2><Dumbbell size={20} />Workout History</h2>
          <p>{detail.workout_history.length} sessions</p>
        </div>
        <div className="admin-table" role="table" aria-label="Workout history">
          <div className="admin-table__header" role="row">
            <span>Session</span>
            <span>Status</span>
            <span>Sets</span>
            <span>Volume</span>
            <span>Started</span>
          </div>
          {detail.workout_history.length ? detail.workout_history.map((session) => (
            <div className="admin-table__row" role="row" key={session.session_id}>
              <strong>{session.session_name}</strong>
              <span>{session.status}</span>
              <span>{session.set_count}</span>
              <span>{session.volume_kg.toLocaleString()} kg</span>
              <time>{parseApiDate(session.completed_at ?? session.started_at).toLocaleString('zh-TW')}</time>
            </div>
          )) : <p className="admin-empty">尚未有訓練紀錄。</p>}
        </div>
      </section>

      <section className="admin-card">
        <div className="section-heading">
          <h2><ListChecks size={20} />Workout Sets</h2>
          <p>{detail.workout_sets.length} rows</p>
        </div>
        <div className="admin-table" role="table" aria-label="Workout sets">
          <div className="admin-table__header" role="row">
            <span>Exercise</span>
            <span>Set</span>
            <span>Weight</span>
            <span>Reps</span>
            <span>Logged</span>
          </div>
          {detail.workout_sets.length ? detail.workout_sets.map((set) => (
            <div className="admin-table__row" role="row" key={set.workout_set_id}>
              <strong>{getExerciseDisplayName(set.exercise, language)}</strong>
              <span>#{set.set_number}</span>
              <span>{set.weight_kg} kg</span>
              <span>{set.reps}</span>
              <time>{parseApiDate(set.logged_at).toLocaleString('zh-TW')}</time>
            </div>
          )) : <p className="admin-empty">尚未有 workout_sets 資料。</p>}
        </div>
      </section>
    </main>
  )
}
