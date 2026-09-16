import { Check, ChevronRight, Dumbbell, Flag, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { apiRequest } from '../api/client'
import type { PlanDay, WorkoutPlan, WorkoutSession, WorkoutSet } from '../api/types'
import { Brand } from '../components/Brand'
import { ErrorNotice } from '../components/ErrorNotice'
import { LoadingScreen } from '../components/LoadingScreen'
import { parseApiDate } from '../lib/datetime'
import {
  getExerciseCues,
  getExerciseImageSrc,
  getExerciseInstructions,
  getExerciseObjective,
  getIntensityTip,
  getPrimaryMuscles,
} from '../lib/exerciseGuidance'
import { getUserId } from '../lib/storage'

interface SetDraft {
  setNumber: number
  weight: string
  reps: string
  saved: boolean
  workoutSetId?: number
}

function formatDuration(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  return [hours, minutes, seconds].map((value) => String(value).padStart(2, '0')).join(':')
}

function draftsForExercise(day: PlanDay, exerciseIndex: number, session: WorkoutSession): SetDraft[] {
  const planExercise = day.exercises[exerciseIndex]
  const existing = session.sets.filter(
    (item) => item.exercise.exercise_id === planExercise.exercise.exercise_id,
  )
  return Array.from({ length: planExercise.target_sets }, (_, index) => {
    const saved = existing.find((item) => item.set_number === index + 1)
    return {
      setNumber: index + 1,
      weight: saved?.weight_kg ?? '',
      reps: saved ? String(saved.reps) : String(planExercise.target_reps),
      saved: Boolean(saved),
      workoutSetId: saved?.workout_set_id,
    }
  })
}

export default function ActiveWorkoutPage() {
  const navigate = useNavigate()
  const userId = getUserId()
  const { planDayId } = useParams()
  const [searchParams] = useSearchParams()
  const initialSessionId = Number(searchParams.get('session'))
  const [plan, setPlan] = useState<WorkoutPlan | null>(null)
  const [session, setSession] = useState<WorkoutSession | null>(null)
  const [exerciseIndex, setExerciseIndex] = useState(0)
  const [drafts, setDrafts] = useState<SetDraft[]>([])
  const [elapsed, setElapsed] = useState(0)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const day = useMemo(
    () => plan?.days.find((item) => item.plan_day_id === Number(planDayId)) ?? null,
    [plan, planDayId],
  )
  const currentExercise = day?.exercises[exerciseIndex]

  useEffect(() => {
    if (!userId || !initialSessionId) return
    let active = true
    Promise.all([
      apiRequest<WorkoutPlan>(`/users/${userId}/plans/active`),
      apiRequest<WorkoutSession>(`/users/${userId}/workouts/sessions/${initialSessionId}`),
    ])
      .then(([planData, sessionData]) => {
        if (!active) return
        setPlan(planData)
        setSession(sessionData)
        const matchedDay = planData.days.find(
          (item) => item.plan_day_id === Number(planDayId),
        )
        if (matchedDay?.exercises.length) {
          setDrafts(draftsForExercise(matchedDay, 0, sessionData))
        }
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message)
      })
    return () => {
      active = false
    }
  }, [initialSessionId, planDayId, userId])

  useEffect(() => {
    if (!session) return
    const startedAt = parseApiDate(session.started_at).getTime()
    const tick = () => setElapsed(Math.max(0, Math.floor((Date.now() - startedAt) / 1000)))
    tick()
    const timer = window.setInterval(tick, 1000)
    return () => window.clearInterval(timer)
  }, [session])

  if (!userId || !initialSessionId) {
    return <main className="empty-page"><h1>找不到進行中的訓練</h1><button className="button button--primary" onClick={() => navigate('/plan')}>返回課表</button></main>
  }
  if ((!plan || !session || !day || !currentExercise) && !error) {
    return <LoadingScreen label="正在準備訓練" />
  }
  if (!plan || !session || !day || !currentExercise) {
    return <main className="page"><ErrorNotice message={error || '找不到這個訓練日。'} /></main>
  }

  const activeSession = session
  const activeExercise = currentExercise
  const activeDay = day
  const savedCount = session.sets.length
  const totalTargetSets = day.exercises.reduce((total, item) => total + item.target_sets, 0)
  const progress = Math.round(((exerciseIndex + 1) / day.exercises.length) * 100)
  const nextExercise = day.exercises[exerciseIndex + 1]
  const currentInstructions = getExerciseInstructions(currentExercise.exercise)
  const primaryMuscles = getPrimaryMuscles(currentExercise.exercise)

  function updateDraft(index: number, field: 'weight' | 'reps', value: string) {
    setDrafts((current) => current.map((draft, draftIndex) => (
      draftIndex === index ? { ...draft, [field]: value, saved: false } : draft
    )))
  }

  async function saveDraft(index: number) {
    const draft = drafts[index]
    const weight = Number(draft.weight)
    const reps = Number(draft.reps)
    if (!Number.isFinite(weight) || weight < 0 || !Number.isInteger(reps) || reps < 1) {
      setError('請輸入有效的 Weight 與 Reps。')
      return
    }
    setBusy(true)
    setError('')
    try {
      let saved: WorkoutSet
      if (draft.workoutSetId) {
        saved = await apiRequest<WorkoutSet>(`/users/${userId}/workouts/sessions/${activeSession.session_id}/sets/${draft.workoutSetId}`, {
          method: 'PATCH',
          body: JSON.stringify({ weight_kg: weight, reps }),
        })
      } else {
        saved = await apiRequest<WorkoutSet>(`/users/${userId}/workouts/sessions/${activeSession.session_id}/sets`, {
          method: 'POST',
          body: JSON.stringify({ exercise_id: activeExercise.exercise.exercise_id, set_number: draft.setNumber, weight_kg: weight, reps }),
        })
      }
      const sessionData = await apiRequest<WorkoutSession>(`/users/${userId}/workouts/sessions/${activeSession.session_id}`)
      setSession(sessionData)
      setDrafts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, saved: true, workoutSetId: saved.workout_set_id } : item))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '儲存本組時發生錯誤。')
    } finally {
      setBusy(false)
    }
  }

  async function completeNextSet() {
    const nextIndex = drafts.findIndex((draft) => !draft.saved)
    if (nextIndex >= 0) {
      await saveDraft(nextIndex)
      return
    }
    if (nextExercise) {
      const nextIndex = exerciseIndex + 1
      setExerciseIndex(nextIndex)
      setDrafts(draftsForExercise(activeDay, nextIndex, activeSession))
    }
  }

  async function finishWorkout() {
    setBusy(true)
    setError('')
    try {
      await apiRequest<WorkoutSession>(`/users/${userId}/workouts/sessions/${activeSession.session_id}/complete`, { method: 'POST' })
      navigate('/dashboard')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '無法完成訓練。')
      setBusy(false)
    }
  }

  return (
    <main className="active-workout">
      <header className="workout-header">
        <Brand />
        <button className="icon-button" type="button" aria-label="關閉訓練" onClick={() => navigate('/plan')}><X size={30} /></button>
      </header>
      <section className="workout-title">
        <div><h1>Day {day.day_number} — {day.focus_summary}</h1><p>專注當下・完成每一組</p></div>
        <div className="workout-timer"><span>訓練時間</span><strong>{formatDuration(elapsed)}</strong></div>
      </section>
      <div className="workout-progress">
        <strong>{exerciseIndex + 1} / {day.exercises.length} 個動作</strong>
        <span className="workout-progress__track"><i style={{ width: `${Math.max(8, progress)}%` }} /></span>
        <span>{progress}%</span>
      </div>

      {error ? <ErrorNotice message={error} /> : null}

      <section className="current-exercise">
        <div className="current-exercise__image">
          <img
            src={getExerciseImageSrc(currentExercise.exercise)}
            alt={`${currentExercise.exercise.exercise_name} 參考圖片`}
          />
        </div>
        <div className="current-exercise__content">
          <span>當前動作</span>
          <h2>{currentExercise.exercise.exercise_name}</h2>
          <p>目標 {currentExercise.target_sets} × {currentExercise.target_reps}・休息 {currentExercise.rest_seconds} 秒</p>
          <p>{getExerciseObjective(currentExercise.exercise)}</p>
          <div className="active-exercise-tags">
            <span>{currentExercise.exercise.body_part.name_zh} / {currentExercise.exercise.body_part.name_en}</span>
            <span>Target: {primaryMuscles.join(', ')}</span>
            <span>{currentExercise.exercise.equipment}</span>
            <span>{currentExercise.exercise.difficulty_level}</span>
          </div>
          <div className="active-exercise-guidance">
            <div>
              <strong>重量建議</strong>
              <p>{getIntensityTip(currentExercise)}</p>
            </div>
            <div>
              <strong>動作重點</strong>
              <ul>
                {getExerciseCues(currentExercise.exercise).map((cue) => <li key={cue}>{cue}</li>)}
              </ul>
            </div>
            <div className="active-exercise-guidance__wide">
              <strong>操作步驟</strong>
              <ol>
                {currentInstructions.map((instruction) => (
                  <li key={instruction}>{instruction}</li>
                ))}
              </ol>
            </div>
          </div>
        </div>
      </section>

      <div className="set-table">
        <div className="set-table__header"><span>Set</span><span>Weight (kg)</span><span>Reps</span><span>狀態</span></div>
        {drafts.map((draft, index) => (
          <div className={`set-row ${draft.saved ? 'is-complete' : ''}`} key={draft.setNumber}>
            <strong>{draft.setNumber}</strong>
            <input aria-label={`第 ${draft.setNumber} 組重量`} inputMode="decimal" value={draft.weight} onChange={(event) => updateDraft(index, 'weight', event.target.value)} />
            <input aria-label={`第 ${draft.setNumber} 組次數`} inputMode="numeric" value={draft.reps} onChange={(event) => updateDraft(index, 'reps', event.target.value)} />
            <button type="button" aria-label={`儲存第 ${draft.setNumber} 組`} onClick={() => saveDraft(index)} disabled={busy}>
              {draft.saved ? <Check size={22} /> : <span />}
            </button>
          </div>
        ))}
      </div>

      <button className="button button--primary workout-primary" type="button" onClick={completeNextSet} disabled={busy}>
        <Dumbbell size={23} />
        {drafts.every((draft) => draft.saved) && nextExercise ? '下一個動作' : '完成本組'}
      </button>

      {nextExercise ? (
        <section className="next-exercise">
          <span>下一個動作</span>
          <div><strong>{nextExercise.exercise.exercise_name}</strong><ChevronRight size={28} /></div>
          <p>目標 {nextExercise.target_sets} × {nextExercise.target_reps}</p>
        </section>
      ) : null}

      <footer className="workout-footer">
        <span>{savedCount} / {totalTargetSets} 組已記錄</span>
        <button className="button button--secondary button--large" type="button" onClick={finishWorkout} disabled={busy || session.sets.length === 0}>
          <Flag size={22} /> 結束訓練
        </button>
      </footer>
    </main>
  )
}
