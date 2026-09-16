import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiRequest } from '../api/client'
import type { BodyPart, Profile, TrainingGoal } from '../api/types'
import { ErrorNotice } from '../components/ErrorNotice'
import { LoadingScreen } from '../components/LoadingScreen'
import { clearUserId, getUserId } from '../lib/storage'

export default function ProfilePage() {
  const navigate = useNavigate()
  const userId = getUserId()
  const [profile, setProfile] = useState<Profile | null>(null)
  const [goals, setGoals] = useState<TrainingGoal[]>([])
  const [parts, setParts] = useState<BodyPart[]>([])
  const [selectedParts, setSelectedParts] = useState<number[]>([])
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (!userId) return
    let active = true
    Promise.all([
      apiRequest<Profile>(`/users/${userId}`),
      apiRequest<TrainingGoal[]>('/reference/training-goals'),
      apiRequest<BodyPart[]>('/reference/body-parts'),
    ]).then(([profileData, goalData, partData]) => {
      if (!active) return
      setProfile(profileData)
      setGoals(goalData)
      setParts(partData)
      setSelectedParts(profileData.preferred_body_parts.map((part) => part.body_part_id))
    }).catch((reason: Error) => {
      if (active) setError(reason.message)
    })
    return () => { active = false }
  }, [userId])

  if (!userId) return <main className="empty-page"><h1>尚未建立健身資料</h1><Link className="button button--primary" to="/onboarding">開始建立</Link></main>
  if (!profile && !error) return <LoadingScreen label="正在載入基本資料" />
  if (!profile) return <main className="page"><ErrorNotice message={error} /></main>

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    setSaved(false)
    setError('')
    try {
      const updated = await apiRequest<Profile>(`/users/${userId}`, {
        method: 'PATCH',
        body: JSON.stringify({
          name: String(data.get('name')),
          gender: data.get('gender') || null,
          age: Number(data.get('age')),
          height_cm: Number(data.get('height_cm')),
          training_experience: data.get('training_experience'),
          training_goal_id: Number(data.get('training_goal_id')),
          training_days_per_week: Number(data.get('training_days_per_week')),
          training_duration_minutes: Number(data.get('training_duration_minutes')),
          preferred_body_part_ids: selectedParts,
        }),
      })
      setProfile(updated)
      setSaved(true)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '無法儲存資料。')
    }
  }

  async function deleteProfile() {
    if (!window.confirm('這會刪除 Profile、課表、訓練與體重紀錄，且無法復原。確定繼續嗎？')) return
    try {
      await apiRequest<void>(`/users/${userId}`, { method: 'DELETE' })
      clearUserId()
      navigate('/')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '無法刪除資料。')
    }
  }

  return (
    <main className="page profile-page">
      <header className="page-heading"><div><h1>編輯資料</h1><p>更新偏好後可回到課表重新產生新的建議。</p></div></header>
      {error ? <ErrorNotice message={error} /> : null}
      {saved ? <div className="success-notice" role="status">資料已更新。</div> : null}
      <form className="profile-form" onSubmit={saveProfile}>
        <div className="form-grid">
          <label className="field"><span>名字</span><input name="name" defaultValue={profile.name} required /></label>
          <label className="field"><span>性別（選填）</span><select name="gender" defaultValue={profile.gender ?? ''}><option value="">不提供</option><option value="female">女性</option><option value="male">男性</option><option value="non_binary">非二元</option><option value="prefer_not_to_say">不便透露</option></select></label>
          <label className="field"><span>年齡</span><input name="age" type="number" min="13" max="100" defaultValue={profile.age} required /></label>
          <label className="field"><span>身高 (cm)</span><input name="height_cm" type="number" min="50" max="300" step="0.1" defaultValue={profile.height_cm} required /></label>
          <label className="field"><span>訓練經驗</span><select name="training_experience" defaultValue={profile.training_experience}><option value="beginner">初學者</option><option value="intermediate">中階者</option><option value="advanced">進階者</option></select></label>
          <label className="field"><span>訓練目標</span><select name="training_goal_id" defaultValue={profile.training_goal.training_goal_id}>{goals.map((goal) => <option key={goal.training_goal_id} value={goal.training_goal_id}>{goal.goal_name}</option>)}</select></label>
          <label className="field"><span>每週訓練天數</span><select name="training_days_per_week" defaultValue={profile.training_days_per_week}>{[2, 3, 4, 5, 6].map((days) => <option key={days} value={days}>{days} days</option>)}</select></label>
          <label className="field"><span>每次時間</span><select name="training_duration_minutes" defaultValue={profile.training_duration_minutes}>{[30, 60, 90].map((minutes) => <option key={minutes} value={minutes}>{minutes} minutes</option>)}</select></label>
        </div>
        <fieldset className="choice-fieldset"><legend>想加強的部位</legend><div className="compact-check-grid">{parts.map((part) => <label key={part.body_part_id}><input type="checkbox" checked={selectedParts.includes(part.body_part_id)} onChange={() => setSelectedParts((current) => current.includes(part.body_part_id) ? current.filter((id) => id !== part.body_part_id) : [...current, part.body_part_id])} /><span>{part.name_en} {part.name_zh}</span></label>)}</div></fieldset>
        <div className="profile-actions"><button className="button button--primary" type="submit">儲存變更</button><button className="button button--danger" type="button" onClick={deleteProfile}>刪除全部資料</button></div>
      </form>
    </main>
  )
}
