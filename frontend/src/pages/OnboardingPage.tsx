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
import { useI18n } from '../i18n'
import { saveUserId } from '../lib/storage'

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
  durationMinutes: 30 | 45 | 60 | 90
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

function ProgressRail({ currentStep, steps }: { currentStep: number; steps: string[] }) {
  return (
    <ol className="progress-rail" aria-label="建立計畫進度">
      {steps.map((label, index) => {
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

function goalLabel(goal: TrainingGoal, language: 'zh-TW' | 'en'): string {
  if (language === 'zh-TW') return goal.goal_name
  const labels: Record<string, string> = {
    muscle_gain: 'Muscle Gain',
    fat_loss: 'Fat Loss',
    strength: 'Strength',
    general_fitness: 'General Fitness',
  }
  return labels[goal.goal_code] ?? goal.goal_name
}

export default function OnboardingPage() {
  const navigate = useNavigate()
  const { language, t, tList } = useI18n()
  const steps = tList('onboarding.steps')
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
    if (step === 6 && form.bodyPartIds.length === 0) return '請至少選擇一個想加強的部位。'
    return ''
  }

  function nextStep() {
    const validationMessage = validateCurrentStep()
    if (validationMessage) {
      setError(validationMessage)
      return
    }
    setError('')
    setStep((current) => Math.min(current + 1, 6))
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
    if (step < 6) {
      nextStep()
      return
    }
    const validationMessage = validateCurrentStep()
    if (validationMessage) {
      setError(validationMessage)
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

  const stepHelp = [
    '提供基本資料，讓資料庫建立唯一 user_id 與初始 body record。',
    t('onboarding.goalHelp'),
    t('onboarding.experienceHelp'),
    t('onboarding.scheduleHelp'),
    t('onboarding.durationHelp'),
    t('onboarding.bodyHelp'),
  ]

  return (
    <main className="onboarding-page">
      <ProgressRail currentStep={step} steps={steps} />
      <form className="onboarding-panel" onSubmit={submit}>
        <header className="onboarding-panel__header">
          <span>Step {step} / 6</span>
          <h1>{steps[step - 1]}</h1>
          <p>{stepHelp[step - 1]}</p>
        </header>

        {error ? <ErrorNotice message={error} /> : null}

        {step === 1 ? (
          <div className="form-grid">
            <label className="field field--wide">
              <span>{t('onboarding.name')} *</span>
              <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Loise" />
              <small>建議使用暱稱；網站沒有 Login / Register。</small>
            </label>
            <label className="field field--wide">
              <span>{t('onboarding.gender')}</span>
              <select value={form.gender} onChange={(event) => setForm({ ...form, gender: event.target.value })}>
                <option value="">不提供 / Prefer not to say</option>
                <option value="female">女性 / Female</option>
                <option value="male">男性 / Male</option>
                <option value="non_binary">非二元 / Non-binary</option>
                <option value="prefer_not_to_say">不便透露 / Prefer not to say</option>
              </select>
            </label>
            <label className="field">
              <span>{t('onboarding.age')} *</span>
              <div className="field__unit"><input type="number" min="13" max="100" value={form.age} onChange={(event) => setForm({ ...form, age: event.target.value })} /><em>歲</em></div>
            </label>
            <label className="field">
              <span>{t('onboarding.height')} *</span>
              <div className="field__unit"><input type="number" min="50" max="300" step="0.1" value={form.heightCm} onChange={(event) => setForm({ ...form, heightCm: event.target.value })} /><em>cm</em></div>
            </label>
            <label className="field">
              <span>{t('onboarding.weight')} *</span>
              <div className="field__unit"><input type="number" min="20" max="500" step="0.1" value={form.weightKg} onChange={(event) => setForm({ ...form, weightKg: event.target.value })} /><em>kg</em></div>
            </label>
          </div>
        ) : null}

        {step === 2 ? (
          <div className="choice-grid choice-grid--two">
            {goals.map((goal) => (
              <ChoiceButton
                key={goal.training_goal_id}
                selected={form.goalId === goal.training_goal_id}
                title={goalLabel(goal, language)}
                description={goal.description ?? undefined}
                icon={<Target size={24} />}
                onClick={() => setForm({ ...form, goalId: goal.training_goal_id })}
              />
            ))}
          </div>
        ) : null}

        {step === 3 ? (
          <fieldset className="choice-fieldset field--full">
            <legend>Training Experience</legend>
            <div className="choice-grid choice-grid--three">
              {[
                ['beginner', '初學者 Beginner', '0–6 個月'],
                ['intermediate', '中階 Intermediate', '6 個月–2 年'],
                ['advanced', '進階 Advanced', '2 年以上'],
              ].map(([value, title, description]) => (
                <ChoiceButton key={value} selected={form.experience === value} title={title} description={description} icon={<Gauge size={22} />} onClick={() => setForm({ ...form, experience: value as FormState['experience'] })} />
              ))}
            </div>
          </fieldset>
        ) : null}

        {step === 4 ? (
          <fieldset className="choice-fieldset">
            <legend>每週可以訓練幾天？</legend>
            <div className="segmented-options segmented-options--large">
              {[2, 3, 4, 5, 6].map((days) => (
                <button type="button" key={days} className={form.daysPerWeek === days ? 'is-selected' : ''} onClick={() => setForm({ ...form, daysPerWeek: days as FormState['daysPerWeek'] })}>{days} days</button>
              ))}
            </div>
          </fieldset>
        ) : null}

        {step === 5 ? (
          <fieldset className="choice-fieldset">
            <legend>每次預計訓練時間？</legend>
            <div className="choice-grid choice-grid--four">
              {[30, 45, 60, 90].map((minutes) => (
                <ChoiceButton
                  key={minutes}
                  selected={form.durationMinutes === minutes}
                  title={`${minutes} minutes`}
                  description={`每天最多 ${minutes === 30 ? 4 : minutes === 45 ? 5 : minutes === 60 ? 6 : 8} 個動作`}
                  icon={<Clock3 size={22} />}
                  onClick={() => setForm({ ...form, durationMinutes: minutes as FormState['durationMinutes'] })}
                />
              ))}
            </div>
          </fieldset>
        ) : null}

        {step === 6 ? (
          <div className="schedule-step">
            <div className="choice-grid choice-grid--two body-part-grid">
              {bodyParts.map((part) => (
                <ChoiceButton
                  key={part.body_part_id}
                  selected={form.bodyPartIds.includes(part.body_part_id)}
                  title={language === 'en' ? `${part.name_en} ${part.name_zh}` : `${part.name_zh} ${part.name_en}`}
                  icon={<Dumbbell size={23} />}
                  onClick={() => toggleBodyPart(part.body_part_id)}
                />
              ))}
            </div>
            <div className="plan-summary">
              <div><span>使用者</span><strong>{form.name || '—'}</strong><small>{form.experience}</small></div>
              <div><span>主要目標</span><strong>{selectedGoal ? goalLabel(selectedGoal, language) : '—'}</strong><small>{selectedGoal?.goal_code}</small></div>
              <div><span>加強部位</span><strong>{selectedParts.map((part) => part.name_zh).join('＋') || '—'}</strong><small>{selectedParts.map((part) => part.name_en).join(', ')}</small></div>
              <div><span>訓練安排</span><strong>每週 {form.daysPerWeek} 天</strong><small>每次 {form.durationMinutes} 分鐘</small></div>
            </div>
          </div>
        ) : null}

        <footer className="onboarding-actions">
          {step > 1 ? (
            <button type="button" className="button button--secondary" onClick={() => { setError(''); setStep((current) => current - 1) }}>
              <ArrowLeft size={19} aria-hidden="true" /> {t('onboarding.buttonBack')}
            </button>
          ) : <span />}
          <button className="button button--primary" type="submit" disabled={submitting}>
            {step === 6 ? (submitting ? t('onboarding.generating') : t('onboarding.buttonGenerate')) : `${t('onboarding.buttonNext')}：${steps[step]}`}
            {!submitting ? <ArrowRight size={20} aria-hidden="true" /> : null}
          </button>
        </footer>
      </form>
    </main>
  )
}
