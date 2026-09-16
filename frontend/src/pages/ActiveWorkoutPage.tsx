import { Check, ChevronRight, Dumbbell, Flag, Plus, TimerReset, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { apiRequest } from '../api/client'
import type { PlanExercise, WorkoutPlan, WorkoutSession, WorkoutSet } from '../api/types'
import { Brand } from '../components/Brand'
import { ErrorNotice } from '../components/ErrorNotice'
import { LoadingScreen } from '../components/LoadingScreen'
import { useI18n } from '../i18n'
import { parseApiDate } from '../lib/datetime'
import {
  getExerciseCues,
  getExerciseDisplayName,
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

interface CompletionSummary {
  durationSeconds: number
  exerciseCount: number
  setCount: number
  volumeKg: number
}

function formatDuration(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  return [hours, minutes, seconds].map((value) => String(value).padStart(2, '0')).join(':')
}

function draftsForExercise(planExercise: PlanExercise, session: WorkoutSession): SetDraft[] {
  const existing = session.sets
    .filter((item) => item.exercise.exercise_id === planExercise.exercise.exercise_id)
    .sort((a, b) => a.set_number - b.set_number)
  const targetLength = Math.max(
    planExercise.target_sets,
    existing.reduce((max, item) => Math.max(max, item.set_number), 0),
  )
  return Array.from({ length: targetLength }, (_, index) => {
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

function sessionSummary(session: WorkoutSession, durationSeconds: number): CompletionSummary {
  const exerciseIds = new Set(session.sets.map((item) => item.exercise.exercise_id))
  return {
    durationSeconds,
    exerciseCount: exerciseIds.size,
    setCount: session.sets.length,
    volumeKg: session.sets.reduce(
      (total, item) => total + Number(item.weight_kg) * item.reps,
      0,
    ),
  }
}

export default function ActiveWorkoutPage() {
  const navigate = useNavigate()
  const { sessionId, planDayId } = useParams()
  const [searchParams] = useSearchParams()
  const { language, t } = useI18n()
  const userId = getUserId()
  const initialSessionId = Number(sessionId ?? searchParams.get('session'))
  const [plan, setPlan] = useState<WorkoutPlan | null>(null)
  const [session, setSession] = useState<WorkoutSession | null>(null)
  const [exerciseIndex, setExerciseIndex] = useState(0)
  const [drafts, setDrafts] = useState<SetDraft[]>([])
  const [elapsed, setElapsed] = useState(0)
  const [restRemaining, setRestRemaining] = useState(0)
  const [completion, setCompletion] = useState<CompletionSummary | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const day = useMemo(() => {
    if (!plan || !session) return null
    const sourcePlanDayId = session.plan_day_id ?? Number(planDayId)
    return plan.days.find((item) => item.plan_day_id === sourcePlanDayId) ?? null
  }, [plan, planDayId, session])
  const currentExercise = day?.exercises[exerciseIndex]

  async function reloadSession(nextSessionId = initialSessionId): Promise<WorkoutSession> {
    const sessionData = await apiRequest<WorkoutSession>(`/users/${userId}/workouts/sessions/${nextSessionId}`)
    setSession(sessionData)
    return sessionData
  }

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
        if (sessionData.status === 'completed') {
          const completedSeconds = sessionData.completed_at
            ? Math.max(0, Math.floor((parseApiDate(sessionData.completed_at).getTime() - parseApiDate(sessionData.started_at).getTime()) / 1000))
            : 0
          setCompletion(sessionSummary(sessionData, completedSeconds))
        }
        const sourcePlanDayId = sessionData.plan_day_id ?? Number(planDayId)
        const matchedDay = planData.days.find((item) => item.plan_day_id === sourcePlanDayId)
        if (matchedDay?.exercises.length) {
          const firstIncompleteIndex = matchedDay.exercises.findIndex((item) => {
            const savedSets = sessionData.sets.filter((set) => set.exercise.exercise_id === item.exercise.exercise_id)
            return savedSets.length < item.target_sets
          })
          setExerciseIndex(firstIncompleteIndex >= 0 ? firstIncompleteIndex : 0)
          setDrafts(draftsForExercise(matchedDay.exercises[firstIncompleteIndex >= 0 ? firstIncompleteIndex : 0], sessionData))
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

  useEffect(() => {
    if (restRemaining <= 0) return
    const timer = window.setInterval(() => {
      setRestRemaining((current) => Math.max(0, current - 1))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [restRemaining])

  useEffect(() => {
    if (!session || !currentExercise) return
    setDrafts(draftsForExercise(currentExercise, session))
  }, [currentExercise, session])

  if (!userId || !initialSessionId) {
    return <main className="empty-page"><h1>{t('workout.missing')}</h1><button className="button button--primary" onClick={() => navigate('/plan')}>返回課表</button></main>
  }
  if ((!plan || !session || !day || !currentExercise) && !error) {
    return <LoadingScreen label={t('workout.loading')} />
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
  const currentInstructions = getExerciseInstructions(currentExercise.exercise, language)
  const primaryMuscles = getPrimaryMuscles(currentExercise.exercise)
  const exerciseName = getExerciseDisplayName(currentExercise.exercise, language)

  if (completion) {
    return (
      <main className="active-workout active-workout--summary">
        <section className="completion-card">
          <span className="completion-card__icon"><Check size={38} /></span>
          <h1>{t('workout.summary')}</h1>
          <p>{activeDay.day_name}</p>
          <div className="completion-metrics">
            <div><span>Duration</span><strong>{formatDuration(completion.durationSeconds)}</strong></div>
            <div><span>Exercises</span><strong>{completion.exerciseCount}</strong></div>
            <div><span>Sets</span><strong>{completion.setCount}</strong></div>
            <div><span>Volume</span><strong>{completion.volumeKg.toLocaleString()} kg</strong></div>
          </div>
          <div className="home-hero__actions">
            <Link className="button button--primary" to="/history">{t('workout.history')}</Link>
            <Link className="button button--secondary" to="/">{t('workout.home')}</Link>
          </div>
        </section>
      </main>
    )
  }

  function updateDraft(index: number, field: 'weight' | 'reps', value: string) {
    setDrafts((current) => current.map((draft, draftIndex) => (
      draftIndex === index ? { ...draft, [field]: value, saved: false } : draft
    )))
  }

  function addSet() {
    setDrafts((current) => [
      ...current,
      {
        setNumber: current.length + 1,
        weight: '',
        reps: String(activeExercise.target_reps),
        saved: false,
      },
    ])
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
      const sessionData = await reloadSession(activeSession.session_id)
      setDrafts(draftsForExercise(activeExercise, sessionData).map((item) => (
        item.setNumber === draft.setNumber ? { ...item, saved: true, workoutSetId: saved.workout_set_id } : item
      )))
      setRestRemaining(activeExercise.rest_seconds)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '儲存本組時發生錯誤。')
    } finally {
      setBusy(false)
    }
  }

  async function completeNextSet() {
    const nextUnsavedIndex = drafts.findIndex((draft) => !draft.saved)
    if (nextUnsavedIndex >= 0) {
      await saveDraft(nextUnsavedIndex)
      return
    }
    if (nextExercise) {
      const nextIndex = exerciseIndex + 1
      setExerciseIndex(nextIndex)
      setDrafts(draftsForExercise(activeDay.exercises[nextIndex], activeSession))
      setRestRemaining(0)
    }
  }

  async function finishWorkout() {
    setBusy(true)
    setError('')
    try {
      const completed = await apiRequest<WorkoutSession>(`/users/${userId}/workouts/sessions/${activeSession.session_id}/complete`, { method: 'POST' })
      setSession(completed)
      setCompletion(sessionSummary(completed, elapsed))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '無法完成訓練。')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="active-workout">
      <header className="workout-header">
        <Brand />
        <button className="icon-button" type="button" aria-label={t('workout.close')} onClick={() => navigate('/plan')}><X size={30} /></button>
      </header>
      <section className="workout-title">
        <div><h1>Day {day.day_number} — {day.focus_summary}</h1><p>專注當下・完成每一組・即時存入 Database</p></div>
        <div className="workout-timer"><span>{t('workout.duration')}</span><strong>{formatDuration(elapsed)}</strong></div>
      </section>
      <div className="workout-progress">
        <strong>{exerciseIndex + 1} / {day.exercises.length} 個動作</strong>
        <span className="workout-progress__track"><i style={{ width: `${Math.max(8, progress)}%` }} /></span>
        <span>{savedCount} / {totalTargetSets} sets</span>
      </div>

      {restRemaining > 0 ? (
        <section className="rest-timer">
          <TimerReset size={22} />
          <div>
            <span>{t('workout.rest')}</span>
            <strong>{restRemaining}s</strong>
          </div>
          <button className="button button--secondary" type="button" onClick={() => setRestRemaining(0)}>
            {t('workout.skipRest')}
          </button>
        </section>
      ) : null}

      {error ? <ErrorNotice message={error} /> : null}

      <section className="current-exercise">
        <div className="current-exercise__image">
          <img
            src={getExerciseImageSrc(currentExercise.exercise)}
            alt={`${exerciseName} 參考圖片`}
          />
        </div>
        <div className="current-exercise__content">
          <span>{t('workout.current')}</span>
          <h2>{exerciseName}</h2>
          <p>目標 {currentExercise.target_sets} × {currentExercise.target_reps}・休息 {currentExercise.rest_seconds} 秒</p>
          <p>{getExerciseObjective(currentExercise.exercise, language)}</p>
          <div className="active-exercise-tags">
            <span>{currentExercise.exercise.body_part.name_zh} / {currentExercise.exercise.body_part.name_en}</span>
            <span>Target: {primaryMuscles.join(', ')}</span>
            <span>{currentExercise.exercise.equipment}</span>
            <span>{currentExercise.exercise.difficulty_level}</span>
          </div>
          <div className="active-exercise-guidance">
            <div>
              <strong>重量建議</strong>
              <p>{getIntensityTip(currentExercise, language)}</p>
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
        <div className="set-table__header"><span>{t('workout.set')}</span><span>{t('workout.weight')}</span><span>{t('workout.reps')}</span><span>{t('workout.status')}</span></div>
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

      <div className="workout-action-row">
        <button className="button button--secondary" type="button" onClick={addSet} disabled={busy}>
          <Plus size={20} /> Add Set
        </button>
        <button className="button button--primary workout-primary" type="button" onClick={completeNextSet} disabled={busy}>
          <Dumbbell size={23} />
          {drafts.every((draft) => draft.saved) && nextExercise ? t('workout.nextExercise') : t('workout.saveSet')}
        </button>
      </div>

      {nextExercise ? (
        <section className="next-exercise">
          <span>{t('workout.nextExercise')}</span>
          <div><strong>{getExerciseDisplayName(nextExercise.exercise, language)}</strong><ChevronRight size={28} /></div>
          <p>目標 {nextExercise.target_sets} × {nextExercise.target_reps}</p>
        </section>
      ) : null}

      <footer className="workout-footer">
        <span>{savedCount} / {totalTargetSets} 組已記錄</span>
        <button className="button button--secondary button--large" type="button" onClick={finishWorkout} disabled={busy || session.sets.length === 0}>
          <Flag size={22} /> {t('workout.finish')}
        </button>
      </footer>
    </main>
  )
}
