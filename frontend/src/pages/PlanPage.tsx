import { Clock3, Dumbbell, Play, RotateCw, Target } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { ChangeEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiRequest } from '../api/client'
import type { PlanExercise, WorkoutPlan, WorkoutSession } from '../api/types'
import { ErrorNotice } from '../components/ErrorNotice'
import { LoadingScreen } from '../components/LoadingScreen'
import {
  getDayObjective,
  getExerciseCues,
  getExerciseImageSrc,
  getExerciseInstructions,
  getExerciseObjective,
  getExerciseRole,
  getIntensityTip,
  getPrimaryMuscles,
} from '../lib/exerciseGuidance'
import { getUserId } from '../lib/storage'

export default function PlanPage() {
  const navigate = useNavigate()
  const userId = getUserId()
  const [plan, setPlan] = useState<WorkoutPlan | null>(null)
  const [selectedDayIndex, setSelectedDayIndex] = useState(0)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!userId) return
    let active = true
    apiRequest<WorkoutPlan>(`/users/${userId}/plans/active`)
      .then((data) => {
        if (active) setPlan(data)
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message)
      })
    return () => {
      active = false
    }
  }, [userId])

  if (!userId) {
    return (
      <main className="empty-page">
        <h1>尚未建立健身資料</h1>
        <p>完成五個步驟後，系統會產生你的第一份訓練課表。</p>
        <Link className="button button--primary" to="/onboarding">開始建立我的健身計畫</Link>
      </main>
    )
  }
  if (!plan && !error) return <LoadingScreen label="正在載入訓練課表" />
  if (!plan) return <main className="page"><ErrorNotice message={error} /></main>

  const activePlan = plan
  const selectedDay = plan.days[selectedDayIndex]
  const mainExercise =
    selectedDay.exercises.find((item) => item.exercise.movement_type === 'compound') ??
    selectedDay.exercises[0]
  const totalTargetSets = selectedDay.exercises.reduce((total, item) => total + item.target_sets, 0)

  async function regeneratePlan() {
    setBusy(true)
    setError('')
    try {
      const nextPlan = await apiRequest<WorkoutPlan>(`/users/${userId}/plans/generate`, {
        method: 'POST',
      })
      setPlan(nextPlan)
      setSelectedDayIndex(0)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '無法重新產生課表。')
    } finally {
      setBusy(false)
    }
  }

  async function startWorkout() {
    setBusy(true)
    setError('')
    try {
      const session = await apiRequest<WorkoutSession>(`/users/${userId}/workouts/sessions`, {
        method: 'POST',
        body: JSON.stringify({ plan_day_id: selectedDay.plan_day_id }),
      })
      navigate(`/workout/${selectedDay.plan_day_id}?session=${session.session_id}`)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '無法開始訓練。')
      setBusy(false)
    }
  }

  async function updatePrescription(
    planExercise: PlanExercise,
    field: 'target_sets' | 'target_reps',
    event: ChangeEvent<HTMLInputElement>,
  ) {
    const value = Number(event.target.value)
    if (!Number.isFinite(value) || value < 1) return
    try {
      const updated = await apiRequest<WorkoutPlan>(
        `/users/${userId}/plans/${activePlan.plan_id}/exercises/${planExercise.plan_exercise_id}`,
        { method: 'PATCH', body: JSON.stringify({ [field]: value }) },
      )
      setPlan(updated)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '更新目標失敗。')
    }
  }

  return (
    <main className="page plan-page">
      <header className="page-heading">
        <div>
          <h1>我的訓練課表</h1>
          <p>規劃屬於你的訓練，持續前進，遇見更強的自己。</p>
        </div>
      </header>
      {error ? <ErrorNotice message={error} /> : null}

      <div className="plan-layout">
        <aside className="day-rail" aria-label="訓練日">
          {plan.days.map((day, index) => (
            <button
              type="button"
              key={day.plan_day_id}
              className={index === selectedDayIndex ? 'is-selected' : ''}
              onClick={() => setSelectedDayIndex(index)}
            >
              <Dumbbell size={22} strokeWidth={2} aria-hidden="true" />
              <span><strong>Day {day.day_number}</strong><small>{day.focus_summary}</small></span>
            </button>
          ))}
        </aside>

        <section className="plan-content">
          <div className="plan-overview">
            <div>
              <h2>{plan.plan_name}</h2>
              <div className="plan-meta">
                <span><Target size={18} /> {plan.training_goal.goal_name}</span>
                <span><Clock3 size={18} /> {plan.training_duration_minutes} minutes</span>
                <span>{plan.algorithm_version}</span>
              </div>
            </div>
            <button className="button button--secondary" type="button" onClick={regeneratePlan} disabled={busy}>
              <RotateCw size={18} aria-hidden="true" />重新產生課表
            </button>
          </div>

          <div className="plan-day-heading">
            <div>
              <h2>Day {selectedDay.day_number}　{selectedDay.focus_summary}</h2>
              <p>{getDayObjective(selectedDay)}</p>
            </div>
            <button className="button button--primary" type="button" onClick={startWorkout} disabled={busy}>
              <Play size={19} fill="currentColor" aria-hidden="true" />
              {busy ? '準備中…' : `開始 Day ${selectedDay.day_number} 訓練`}
            </button>
          </div>

          <section className="today-brief" aria-label="今日訓練重點">
            <div>
              <span>今日主要任務</span>
              <strong>{mainExercise.exercise.exercise_name}</strong>
              <p>{getExerciseObjective(mainExercise.exercise)}</p>
            </div>
            <div>
              <span>預計訓練量</span>
              <strong>{selectedDay.exercises.length} 個動作・{totalTargetSets} 組</strong>
              <p>每個動作都有參考圖片、動作重點與建議強度；組數與次數可直接修改。</p>
            </div>
          </section>

          <div className="plan-exercise-cards" aria-label={`${selectedDay.day_name} 詳細動作`}>
            {selectedDay.exercises.map((item, index) => {
              const cues = getExerciseCues(item.exercise)
              const instructions = getExerciseInstructions(item.exercise)
              const primaryMuscles = getPrimaryMuscles(item.exercise)
              return (
                <article className="plan-exercise-card" key={item.plan_exercise_id}>
                  <div className="exercise-reference">
                    <img src={getExerciseImageSrc(item.exercise)} alt={`${item.exercise.exercise_name} 參考圖片`} />
                    <span>{getExerciseRole(item, index)}</span>
                  </div>
                  <div className="plan-exercise-card__body">
                    <div className="exercise-card-heading">
                      <div>
                        <span>#{item.exercise_order}・{item.exercise.body_part.name_zh} / {item.exercise.body_part.name_en}</span>
                        <h3>{item.exercise.exercise_name}</h3>
                      </div>
                      <div className="exercise-tags">
                        <span>{item.exercise.difficulty_level}</span>
                        <span>{item.exercise.equipment}</span>
                        <span>{item.exercise.movement_type}</span>
                      </div>
                    </div>
                    <p className="exercise-description">{item.exercise.description}</p>
                    <p className="exercise-objective">{getExerciseObjective(item.exercise)}</p>
                    <div className="exercise-prescription-panel">
                      <label>
                        <span>目標組數</span>
                        <input aria-label={`${item.exercise.exercise_name} 組數`} type="number" min="1" max="6" defaultValue={item.target_sets} onBlur={(event) => updatePrescription(item, 'target_sets', event)} />
                      </label>
                      <label>
                        <span>每組次數</span>
                        <input aria-label={`${item.exercise.exercise_name} 次數`} type="number" min="1" max="30" defaultValue={item.target_reps} onBlur={(event) => updatePrescription(item, 'target_reps', event)} />
                      </label>
                      <div>
                        <span>休息時間</span>
                        <strong>{item.rest_seconds} 秒</strong>
                      </div>
                    </div>
                    <div className="exercise-guidance-grid">
                      <div>
                        <span>重量建議</span>
                        <p>{getIntensityTip(item)}</p>
                      </div>
                      <div>
                        <span>動作重點</span>
                        <ul>
                          {cues.map((cue) => <li key={cue}>{cue}</li>)}
                        </ul>
                      </div>
                    </div>
                    <details className="exercise-detail-panel">
                      <summary>查看完整動作示範與步驟</summary>
                      <div className="exercise-detail-panel__content">
                        <div className="exercise-demo-frame">
                          <img
                            src={getExerciseImageSrc(item.exercise)}
                            alt={`${item.exercise.exercise_name} 動作示範`}
                          />
                          <span>{item.exercise.gif_url ? 'GIF Demo' : 'Local Reference Image'}</span>
                        </div>
                        <div className="exercise-detail-copy">
                          <div className="exercise-muscle-grid">
                            <div>
                              <span>主要訓練肌群</span>
                              <p>{primaryMuscles.join(', ')}</p>
                            </div>
                            <div>
                              <span>輔助肌群</span>
                              <p>{item.exercise.secondary_muscles.length ? item.exercise.secondary_muscles.join(', ') : '依動作穩定需求啟動核心與協同肌群'}</p>
                            </div>
                          </div>
                          <ol>
                            {instructions.map((instruction) => (
                              <li key={instruction}>{instruction}</li>
                            ))}
                          </ol>
                          <p>
                            建議安排：{item.target_sets} 組 × {item.target_reps} 下，
                            組間休息 {item.rest_seconds} 秒。{getIntensityTip(item)}
                          </p>
                        </div>
                      </div>
                    </details>
                  </div>
                </article>
              )
            })}
          </div>
        </section>
      </div>
    </main>
  )
}
