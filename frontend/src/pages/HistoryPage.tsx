import { Activity, CalendarDays, Plus, Scale, Search, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { apiRequest } from '../api/client'
import type { BodyRecord, WorkoutSession } from '../api/types'
import { ErrorNotice } from '../components/ErrorNotice'
import { LoadingScreen } from '../components/LoadingScreen'
import { parseApiDate } from '../lib/datetime'
import { getUserId } from '../lib/storage'

function fetchHistory(userId: string) {
  return Promise.all([
    apiRequest<WorkoutSession[]>(`/users/${userId}/workouts/sessions?status_filter=completed`),
    apiRequest<BodyRecord[]>(`/users/${userId}/body-records`),
  ])
}

export default function HistoryPage() {
  const userId = getUserId()
  const [sessions, setSessions] = useState<WorkoutSession[]>([])
  const [records, setRecords] = useState<BodyRecord[]>([])
  const [weight, setWeight] = useState('')
  const [recordedOn, setRecordedOn] = useState(new Date().toISOString().slice(0, 10))
  const [exerciseSearch, setExerciseSearch] = useState('')
  const [selectedExercise, setSelectedExercise] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadHistory = useCallback(async (showLoading = false) => {
    if (!userId) return
    if (showLoading) setLoading(true)
    try {
      const [sessionData, recordData] = await fetchHistory(userId)
      setSessions(sessionData)
      setRecords(recordData)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '無法載入歷史紀錄。')
    } finally {
      setLoading(false)
    }
  }, [userId])

  useEffect(() => {
    if (!userId) return
    let active = true
    fetchHistory(userId)
      .then(([sessionData, recordData]) => {
        if (!active) return
        setSessions(sessionData)
        setRecords(recordData)
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message)
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [userId])

  const exerciseSummary = useMemo(() => {
    const summary = new Map<string, { sets: number; volume: number }>()
    for (const session of sessions) {
      for (const item of session.sets.filter((set) => !set.is_warmup)) {
        const current = summary.get(item.exercise.exercise_name) ?? { sets: 0, volume: 0 }
        current.sets += 1
        current.volume += Number(item.weight_kg) * item.reps
        summary.set(item.exercise.exercise_name, current)
      }
    }
    return [...summary.entries()].sort((a, b) => b[1].sets - a[1].sets)
  }, [sessions])
  const exerciseDetails = useMemo(() => {
    const details = new Map<string, Array<{
      key: string
      date: string
      sessionName: string
      setNumber: number
      weight: string
      reps: number
      volume: number
    }>>()
    for (const session of sessions) {
      for (const set of session.sets.filter((item) => !item.is_warmup)) {
        const name = set.exercise.exercise_name
        const rows = details.get(name) ?? []
        rows.push({
          key: `${session.session_id}-${set.workout_set_id}`,
          date: parseApiDate(session.started_at).toLocaleDateString('zh-TW'),
          sessionName: session.session_name,
          setNumber: set.set_number,
          weight: set.weight_kg,
          reps: set.reps,
          volume: Number(set.weight_kg) * set.reps,
        })
        details.set(name, rows)
      }
    }
    return details
  }, [sessions])
  const filteredExerciseSummary = useMemo(() => (
    exerciseSummary.filter(([name]) => name.toLowerCase().includes(exerciseSearch.trim().toLowerCase()))
  ), [exerciseSearch, exerciseSummary])
  const activeExerciseName = selectedExercise || filteredExerciseSummary[0]?.[0] || ''
  const activeExerciseRows = exerciseDetails.get(activeExerciseName) ?? []

  if (!userId) return <main className="empty-page"><h1>尚未建立健身資料</h1><Link className="button button--primary" to="/onboarding">開始建立</Link></main>
  if (loading) return <LoadingScreen label="正在載入歷史紀錄" />

  async function addWeight(event: FormEvent) {
    event.preventDefault()
    if (!weight) return
    setError('')
    try {
      await apiRequest<BodyRecord>(`/users/${userId}/body-records`, {
        method: 'POST',
        body: JSON.stringify({ recorded_on: recordedOn, weight_kg: Number(weight) }),
      })
      setWeight('')
      await loadHistory(true)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '無法新增體重紀錄。')
    }
  }

  async function deleteSession(sessionId: number) {
    if (!window.confirm('確定刪除這次訓練與所有 Set 紀錄嗎？')) return
    try {
      await apiRequest<void>(`/users/${userId}/workouts/sessions/${sessionId}`, { method: 'DELETE' })
      await loadHistory(true)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '無法刪除訓練紀錄。')
    }
  }

  async function deleteBodyRecord(recordId: number) {
    if (!window.confirm('確定刪除這筆體重紀錄嗎？')) return
    try {
      await apiRequest<void>(`/users/${userId}/body-records/${recordId}`, { method: 'DELETE' })
      await loadHistory(true)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '無法刪除體重紀錄。')
    }
  }

  return (
    <main className="page history-page">
      <header className="page-heading"><div><h1>歷史紀錄</h1><p>查看每次完成的 Set、Exercise 表現與體重變化。</p></div></header>
      {error ? <ErrorNotice message={error} /> : null}

      <section className="history-section">
        <div className="section-heading"><div><CalendarDays size={24} /><h2>Workout History</h2></div><span>{sessions.length} 次完成</span></div>
        {sessions.length ? (
          <div className="history-list">
            {sessions.map((session) => {
              const volume = session.sets.filter((set) => !set.is_warmup).reduce((total, set) => total + Number(set.weight_kg) * set.reps, 0)
              return (
                <details className="history-row" key={session.session_id}>
                  <summary>
                    <time>{new Intl.DateTimeFormat('zh-TW', { month: '2-digit', day: '2-digit', weekday: 'short' }).format(parseApiDate(session.started_at))}</time>
                    <strong>{session.session_name}</strong>
                    <span>{session.sets.length} 組</span>
                    <span>{volume.toLocaleString()} kg</span>
                    <button type="button" aria-label="刪除訓練" onClick={(event) => { event.preventDefault(); void deleteSession(session.session_id) }}><Trash2 size={17} /></button>
                  </summary>
                  <div className="history-row__sets">
                    {session.sets.map((set) => (
                      <div key={set.workout_set_id}><span>{set.exercise.exercise_name}</span><span>Set {set.set_number}</span><strong>{set.weight_kg} kg × {set.reps}</strong></div>
                    ))}
                  </div>
                </details>
              )
            })}
          </div>
        ) : <p className="empty-inline">尚未完成訓練。從課表開始第一天吧。</p>}
      </section>

      <div className="history-columns">
        <section className="history-section">
          <div className="section-heading"><div><Activity size={24} /><h2>Exercise History</h2></div></div>
          <label className="search-field history-search"><Search size={18} /><input value={exerciseSearch} onChange={(event) => { setExerciseSearch(event.target.value); setSelectedExercise('') }} placeholder="搜尋 Exercise progress" /></label>
          <div className="ranked-list">
            {filteredExerciseSummary.slice(0, 8).map(([name, item], index) => (
              <button className={activeExerciseName === name ? 'is-selected' : ''} type="button" key={name} onClick={() => setSelectedExercise(name)}><span>{String(index + 1).padStart(2, '0')}</span><strong>{name}</strong><small>{item.sets} 組</small><em>{item.volume.toLocaleString()} kg</em></button>
            ))}
          </div>
          {activeExerciseName ? (
            <div className="exercise-progress-table">
              <h3>{activeExerciseName} Progress</h3>
              {activeExerciseRows.map((row) => (
                <div key={row.key}>
                  <time>{row.date}</time>
                  <span>{row.sessionName}</span>
                  <strong>Set {row.setNumber}: {row.weight}kg × {row.reps}</strong>
                  <em>{row.volume.toLocaleString()} kg</em>
                </div>
              ))}
            </div>
          ) : <p className="empty-inline">尚未有 Exercise 紀錄。</p>}
        </section>
        <section className="history-section">
          <div className="section-heading"><div><Scale size={24} /><h2>Weight History</h2></div></div>
          <form className="weight-form" onSubmit={addWeight}>
            <label><span>日期</span><input type="date" value={recordedOn} onChange={(event) => setRecordedOn(event.target.value)} /></label>
            <label><span>體重</span><div className="field__unit"><input type="number" min="20" max="500" step="0.1" value={weight} onChange={(event) => setWeight(event.target.value)} placeholder="68.4" /><em>kg</em></div></label>
            <button className="button button--primary" type="submit"><Plus size={18} />新增</button>
          </form>
          <div className="weight-list">
            {[...records].reverse().map((record) => (
              <div key={record.body_record_id}><time>{record.recorded_on}</time><strong>{record.weight_kg} kg</strong><button type="button" aria-label={`刪除 ${record.recorded_on} 體重紀錄`} onClick={() => void deleteBodyRecord(record.body_record_id)}><Trash2 size={16} /></button></div>
            ))}
          </div>
        </section>
      </div>
    </main>
  )
}
