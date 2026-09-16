import {
  ArrowLeft,
  ArrowRight,
  Check,
  Clock3,
  Dumbbell,
  Gauge,
  Target,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiRequest } from '../api/client'
import type { BodyPart, Profile, TrainingGoal, WorkoutPlan } from '../api/types'
import { ErrorNotice } from '../components/ErrorNotice'
import { saveUserId } from '../lib/storage'

const STEPS = ['基本資料', '健身目標', '加強部位', '訓練安排', '產生課表']

interface FormState {
  name: string
  gender: string
  age: string
  heightCm: string
  weightKg: string
  experience: 'beginner' | 'intermediate' | 'advanced'
  goalId: number | null
  bodyPartIds: number[]
  daysPerWeek: 2 | 3 | 4 | 5 | 6
  durationMinutes: 30 | 60 | 90
}

const INITIAL_FORM: FormState = {
  name: '',
  gender: '',
  age: '',
  heightCm: '',
  weightKg: '',
  experience: 'beginner',
  goalId: null,
  bodyPartIds: [],
  daysPerWeek: 4,
  durationMinutes: 60,
}

function ProgressRail({ currentStep }: { currentStep: number }) {
  return (
    <ol className="progress-rail" aria-label="建立計畫進度">
      {STEPS.map((label, index) => {
        const number = index + 1
        return (
          <li
            key={label}
            className={`progress-rail__item ${number === currentStep ? 'is-current' : ''} ${number < currentStep ? 'is-complete' : ''}`}
            aria-current={number === currentStep ? 'step' : undefined}
          >
            <span className="progress-rail__number">
              {number < currentStep ? <Check size={16} aria-hidden="true" /> : number}
            </span>
            <span>{label}</span>
          </li>
        )
      })}
    </ol>
  )
}

function ChoiceButton({
  selected,
  title,
  description,
  onClick,
  icon,
}: {
  selected: boolean
  title: string
  description?: string
  onClick: () => void
  icon?: ReactNode
}) {
  return (
    <button
      className={`choice-button ${selected ? 'is-selected' : ''}`}
      type="button"
      aria-pressed={selected}
      onClick={onClick}
    >
      {icon ? <span className="choice-button__icon">{icon}</span> : null}
      <span>
        <strong>{title}</strong>
        {description ? <small>{description}</small> : null}
      </span>
      <span className="choice-button__check" aria-hidden="true">
        {selected ? <Check size={17} /> : null}
      </span>
    </button>
  )
}

export default function OnboardingPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [form, setForm] = useState<FormState>(INITIAL_FORM)
  const [goals, setGoals] = useState<TrainingGoal[]>([])
  const [bodyParts, setBodyParts] = useState<BodyPart[]>([])
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    let active = true
    Promise.all([
      apiRequest<TrainingGoal[]>('/reference/training-goals'),
      apiRequest<BodyPart[]>('/reference/body-parts'),
    ])
      .then(([goalData, partData]) => {
        if (!active) return
        setGoals(goalData)
        setBodyParts(partData)
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message)
      })
    return () => {
      active = false
    }
  }, [])

  const selectedGoal = useMemo(
    () => goals.find((goal) => goal.training_goal_id === form.goalId),
    [form.goalId, goals],
  )
  const selectedParts = useMemo(
    () => bodyParts.filter((part) => form.bodyPartIds.includes(part.body_part_id)),
    [bodyParts, form.bodyPartIds],
  )

  function validateCurrentStep(): string {
    if (step === 1) {
      if (!form.name.trim()) return '請輸入名字。'
      if (!form.age || Number(form.age) < 13 || Number(form.age) > 100) return '年齡需介於 13 到 100 歲。'
      if (!form.heightCm || Number(form.heightCm) < 50 || Number(form.heightCm) > 300) return '請輸入有效身高。'
      if (!form.weightKg || Number(form.weightKg) < 20 || Number(form.weightKg) > 500) return '請輸入有效體重。'
    }
    if (step === 2 && form.goalId === null) return '請選擇一個健身目標。'
    if (step === 3 && form.bodyPartIds.length === 0) return '請至少選擇一個想加強的部位。'
    return ''
  }

  function nextStep() {
    const validationMessage = validateCurrentStep()
    if (validationMessage) {
      setError(validationMessage)
      return
    }
    setError('')
    setStep((current) => Math.min(current + 1, 5))
  }

  function toggleBodyPart(bodyPartId: number) {
    setForm((current) => ({
      ...current,
      bodyPartIds: current.bodyPartIds.includes(bodyPartId)
        ? current.bodyPartIds.filter((id) => id !== bodyPartId)
        : [...current.bodyPartIds, bodyPartId],
    }))
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (step < 5) {
      nextStep()
      return
    }
    setSubmitting(true)
    setError('')
    try {
      const profile = await apiRequest<Profile>('/users', {
        method: 'POST',
        body: JSON.stringify({
          name: form.name.trim(),
          gender: form.gender || null,
          age: Number(form.age),
          height_cm: Number(form.heightCm),
          weight_kg: Number(form.weightKg),
          training_experience: form.experience,
          training_goal_id: form.goalId,
          training_days_per_week: form.daysPerWeek,
          training_duration_minutes: form.durationMinutes,
          preferred_body_part_ids: form.bodyPartIds,
        }),
      })
      saveUserId(profile.user_id)
      await apiRequest<WorkoutPlan>(`/users/${profile.user_id}/plans/generate`, { method: 'POST' })
      navigate('/plan')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '建立課表時發生錯誤。')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="onboarding-page">
      <ProgressRail currentStep={step} />
      <form className="onboarding-panel" onSubmit={submit}>
        <header className="onboarding-panel__header">
          <span>Step {step} / 5</span>
          <h1>{STEPS[step - 1]}</h1>
          <p>
            {step === 1 ? '提供基本資料，讓課表符合你的訓練階段。' : null}
            {step === 2 ? '選擇目前最重要的一個訓練方向。' : null}
            {step === 3 ? '可複選；重點部位會獲得較高的每週訓練頻率。' : null}
            {step === 4 ? '依照你實際可投入的時間安排每週內容。' : null}
            {step === 5 ? '確認內容後，由 rules-v1 產生平衡的建議課表。' : null}
          </p>
        </header>

        {error ? <ErrorNotice message={error} /> : null}

        {step === 1 ? (
          <div className="form-grid">
            <label className="field field--wide">
              <span>名字 *</span>
              <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="請輸入你的名字或暱稱" />
              <small>建議使用暱稱；網站沒有登入或隱私保護。</small>
            </label>
            <label className="field field--wide">
              <span>性別（選填）</span>
              <select value={form.gender} onChange={(event) => setForm({ ...form, gender: event.target.value })}>
                <option value="">不提供</option>
                <option value="female">女性</option>
                <option value="male">男性</option>
                <option value="non_binary">非二元</option>
                <option value="prefer_not_to_say">不便透露</option>
              </select>
            </label>
            <label className="field">
              <span>年齡 *</span>
              <div className="field__unit"><input type="number" min="13" max="100" value={form.age} onChange={(event) => setForm({ ...form, age: event.target.value })} /><em>歲</em></div>
            </label>
            <label className="field">
              <span>身高 *</span>
              <div className="field__unit"><input type="number" min="50" max="300" step="0.1" value={form.heightCm} onChange={(event) => setForm({ ...form, heightCm: event.target.value })} /><em>cm</em></div>
            </label>
            <label className="field">
              <span>體重 *</span>
              <div className="field__unit"><input type="number" min="20" max="500" step="0.1" value={form.weightKg} onChange={(event) => setForm({ ...form, weightKg: event.target.value })} /><em>kg</em></div>
            </label>
            <fieldset className="choice-fieldset field--full">
              <legend>訓練經驗 *</legend>
              <div className="choice-grid choice-grid--three">
                {[
                  ['beginner', '初學者', '0–6 個月'],
                  ['intermediate', '中階者', '6 個月–2 年'],
                  ['advanced', '進階者', '2 年以上'],
                ].map(([value, title, description]) => (
                  <ChoiceButton key={value} selected={form.experience === value} title={title} description={description} icon={<Gauge size={22} />} onClick={() => setForm({ ...form, experience: value as FormState['experience'] })} />
                ))}
              </div>
            </fieldset>
          </div>
        ) : null}

        {step === 2 ? (
          <div className="choice-grid choice-grid--two">
            {goals.map((goal) => (
              <ChoiceButton key={goal.training_goal_id} selected={form.goalId === goal.training_goal_id} title={goal.goal_name} description={goal.description ?? undefined} icon={<Target size={24} />} onClick={() => setForm({ ...form, goalId: goal.training_goal_id })} />
            ))}
          </div>
        ) : null}

        {step === 3 ? (
          <div className="choice-grid choice-grid--two body-part-grid">
            {bodyParts.map((part) => (
              <ChoiceButton key={part.body_part_id} selected={form.bodyPartIds.includes(part.body_part_id)} title={`${part.name_en} ${part.name_zh}`} icon={<Dumbbell size={23} />} onClick={() => toggleBodyPart(part.body_part_id)} />
            ))}
          </div>
        ) : null}

        {step === 4 ? (
          <div className="schedule-step">
            <fieldset className="choice-fieldset">
              <legend>每週可以訓練幾天？</legend>
              <div className="segmented-options">
                {[2, 3, 4, 5, 6].map((days) => (
                  <button type="button" key={days} className={form.daysPerWeek === days ? 'is-selected' : ''} onClick={() => setForm({ ...form, daysPerWeek: days as FormState['daysPerWeek'] })}>{days} days</button>
                ))}
              </div>
            </fieldset>
            <fieldset className="choice-fieldset">
              <legend>每次預計訓練時間？</legend>
              <div className="choice-grid choice-grid--three">
                {[30, 60, 90].map((minutes) => (
                  <ChoiceButton key={minutes} selected={form.durationMinutes === minutes} title={`${minutes} minutes`} description={`每次最多 ${minutes === 30 ? 4 : minutes === 60 ? 6 : 8} 個動作`} icon={<Clock3 size={22} />} onClick={() => setForm({ ...form, durationMinutes: minutes as FormState['durationMinutes'] })} />
                ))}
              </div>
            </fieldset>
          </div>
        ) : null}

        {step === 5 ? (
          <div className="plan-summary">
            <div><span>使用者</span><strong>{form.name}</strong><small>{form.experience}</small></div>
            <div><span>主要目標</span><strong>{selectedGoal?.goal_name}</strong><small>{selectedGoal?.goal_code}</small></div>
            <div><span>加強部位</span><strong>{selectedParts.map((part) => part.name_zh).join('＋')}</strong><small>{selectedParts.map((part) => part.name_en).join(', ')}</small></div>
            <div><span>訓練安排</span><strong>每週 {form.daysPerWeek} 天</strong><small>每次 {form.durationMinutes} 分鐘</small></div>
          </div>
        ) : null}

        <footer className="onboarding-actions">
          {step > 1 ? (
            <button type="button" className="button button--secondary" onClick={() => { setError(''); setStep((current) => current - 1) }}>
              <ArrowLeft size={19} aria-hidden="true" /> 上一步
            </button>
          ) : <span />}
          <button className="button button--primary" type="submit" disabled={submitting}>
            {step === 5 ? (submitting ? '正在產生課表…' : '產生我的訓練課表') : `下一步：${STEPS[step]}`}
            {!submitting ? <ArrowRight size={20} aria-hidden="true" /> : null}
          </button>
        </footer>
      </form>
    </main>
  )
}
