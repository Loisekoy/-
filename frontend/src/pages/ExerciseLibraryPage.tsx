import { Edit3, Plus, RotateCcw, Search, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { apiRequest } from '../api/client'
import type { BodyPart, Exercise } from '../api/types'
import { ErrorNotice } from '../components/ErrorNotice'
import { LoadingScreen } from '../components/LoadingScreen'
import { getUserId } from '../lib/storage'

interface ExerciseFormState {
  exercise_name: string
  body_part_id: string
  difficulty_level: 'beginner' | 'intermediate' | 'advanced'
  equipment: string
  movement_type: 'compound' | 'isolation'
  description: string
  image_url: string
  is_active: boolean
}

const EMPTY_FORM: ExerciseFormState = {
  exercise_name: '',
  body_part_id: '',
  difficulty_level: 'beginner',
  equipment: '',
  movement_type: 'compound',
  description: '',
  image_url: '',
  is_active: true,
}

function formFromExercise(exercise: Exercise): ExerciseFormState {
  return {
    exercise_name: exercise.exercise_name,
    body_part_id: String(exercise.body_part.body_part_id),
    difficulty_level: exercise.difficulty_level as ExerciseFormState['difficulty_level'],
    equipment: exercise.equipment,
    movement_type: exercise.movement_type as ExerciseFormState['movement_type'],
    description: exercise.description,
    image_url: exercise.image_url ?? '',
    is_active: exercise.is_active,
  }
}

export default function ExerciseLibraryPage() {
  const userId = getUserId()
  const [bodyParts, setBodyParts] = useState<BodyPart[]>([])
  const [exercises, setExercises] = useState<Exercise[]>([])
  const [search, setSearch] = useState('')
  const [bodyPartId, setBodyPartId] = useState('')
  const [difficulty, setDifficulty] = useState('')
  const [includeInactive, setIncludeInactive] = useState(false)
  const [form, setForm] = useState<ExerciseFormState>(EMPTY_FORM)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState('')

  const queryString = useMemo(() => {
    const params = new URLSearchParams()
    if (search.trim()) params.set('search', search.trim())
    if (bodyPartId) params.set('body_part_id', bodyPartId)
    if (difficulty) params.set('difficulty_level', difficulty)
    if (includeInactive) params.set('include_inactive', 'true')
    const suffix = params.toString()
    return suffix ? `?${suffix}` : ''
  }, [bodyPartId, difficulty, includeInactive, search])

  const loadData = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true)
    try {
      const [partsPayload, exercisePayload] = await Promise.all([
        apiRequest<BodyPart[]>('/reference/body-parts'),
        apiRequest<Exercise[]>(`/reference/exercises${queryString}`),
      ])
      setBodyParts(partsPayload)
      setExercises(exercisePayload)
      setForm((current) => ({
        ...current,
        body_part_id: current.body_part_id || String(partsPayload[0]?.body_part_id ?? ''),
      }))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '無法載入 Exercise Database。')
    } finally {
      setLoading(false)
    }
  }, [queryString])

  useEffect(() => {
    let active = true
    Promise.all([
      apiRequest<BodyPart[]>('/reference/body-parts'),
      apiRequest<Exercise[]>(`/reference/exercises${queryString}`),
    ])
      .then(([partsPayload, exercisePayload]) => {
        if (!active) return
        setBodyParts(partsPayload)
        setExercises(exercisePayload)
        setForm((current) => ({
          ...current,
          body_part_id: current.body_part_id || String(partsPayload[0]?.body_part_id ?? ''),
        }))
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
  }, [queryString])

  function resetForm(clearNotice = true) {
    setEditingId(null)
    if (clearNotice) setSaved('')
    setForm({
      ...EMPTY_FORM,
      body_part_id: String(bodyParts[0]?.body_part_id ?? ''),
    })
  }

  async function submitExercise(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setSaved('')
    try {
      const payload = {
        exercise_name: form.exercise_name.trim(),
        body_part_id: Number(form.body_part_id),
        difficulty_level: form.difficulty_level,
        equipment: form.equipment.trim(),
        movement_type: form.movement_type,
        description: form.description.trim(),
        image_url: form.image_url.trim() || null,
        ...(editingId ? { is_active: form.is_active } : {}),
      }
      if (editingId) {
        await apiRequest<Exercise>(`/exercises/${editingId}`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
        setSaved('Exercise 已更新。')
      } else {
        await apiRequest<Exercise>('/exercises', {
          method: 'POST',
          body: JSON.stringify(payload),
        })
        setSaved('Exercise 已新增。')
      }
      resetForm(false)
      await loadData()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '無法儲存 Exercise。')
    } finally {
      setSaving(false)
    }
  }

  async function deleteExercise(exercise: Exercise) {
    if (!window.confirm(`確定刪除 ${exercise.exercise_name}？若已被課表或訓練引用，系統會改為停用。`)) return
    setError('')
    setSaved('')
    try {
      await apiRequest<void>(`/exercises/${exercise.exercise_id}`, { method: 'DELETE' })
      setSaved('Exercise 已刪除或停用。')
      await loadData()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '無法刪除 Exercise。')
    }
  }

  if (!userId) {
    return (
      <main className="empty-page">
        <h1>尚未建立健身資料</h1>
        <Link className="button button--primary" to="/onboarding">開始建立</Link>
      </main>
    )
  }
  if (loading) return <LoadingScreen label="正在載入 Exercise Database" />

  return (
    <main className="page exercise-library-page">
      <header className="page-heading">
        <div>
          <h1>動作資料庫</h1>
          <p>搜尋、篩選、新增、修改與刪除 Exercise，展示完整 CRUD 與資料庫關聯。</p>
        </div>
      </header>
      {error ? <ErrorNotice message={error} /> : null}
      {saved ? <div className="success-notice" role="status">{saved}</div> : null}

      <section className="exercise-library-layout">
        <aside className="exercise-editor">
          <div className="section-heading">
            <h2>{editingId ? '修改 Exercise' : '新增 Exercise'}</h2>
            {editingId ? <button type="button" onClick={() => resetForm()}><RotateCcw size={16} />取消</button> : null}
          </div>
          <form onSubmit={submitExercise}>
            <label className="field"><span>Exercise Name</span><input required value={form.exercise_name} onChange={(event) => setForm({ ...form, exercise_name: event.target.value })} /></label>
            <label className="field"><span>Body Part</span><select required value={form.body_part_id} onChange={(event) => setForm({ ...form, body_part_id: event.target.value })}>{bodyParts.map((part) => <option key={part.body_part_id} value={part.body_part_id}>{part.name_en} {part.name_zh}</option>)}</select></label>
            <label className="field"><span>Difficulty</span><select value={form.difficulty_level} onChange={(event) => setForm({ ...form, difficulty_level: event.target.value as ExerciseFormState['difficulty_level'] })}><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select></label>
            <label className="field"><span>Equipment</span><input required value={form.equipment} onChange={(event) => setForm({ ...form, equipment: event.target.value })} placeholder="Barbell, Cable, Bodyweight..." /></label>
            <label className="field"><span>Movement Type</span><select value={form.movement_type} onChange={(event) => setForm({ ...form, movement_type: event.target.value as ExerciseFormState['movement_type'] })}><option value="compound">Compound</option><option value="isolation">Isolation</option></select></label>
            <label className="field"><span>Image URL</span><input value={form.image_url} onChange={(event) => setForm({ ...form, image_url: event.target.value })} placeholder="/exercise-images/chest.svg" /></label>
            {editingId ? <label className="toggle-line"><input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} /><span>Active</span></label> : null}
            <label className="field"><span>Description</span><textarea required value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} rows={4} /></label>
            <button className="button button--primary" type="submit" disabled={saving}><Plus size={18} />{saving ? '儲存中…' : editingId ? '儲存修改' : '新增 Exercise'}</button>
          </form>
        </aside>

        <section className="exercise-library-list">
          <div className="exercise-filters">
            <label className="search-field"><Search size={18} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜尋 Bench、Squat、Cable..." /></label>
            <select aria-label="依身體部位篩選" value={bodyPartId} onChange={(event) => setBodyPartId(event.target.value)}><option value="">全部部位</option>{bodyParts.map((part) => <option key={part.body_part_id} value={part.body_part_id}>{part.name_en}</option>)}</select>
            <select aria-label="依難度篩選" value={difficulty} onChange={(event) => setDifficulty(event.target.value)}><option value="">全部難度</option><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select>
            <label className="toggle-line"><input type="checkbox" checked={includeInactive} onChange={(event) => setIncludeInactive(event.target.checked)} /><span>顯示停用</span></label>
          </div>
          <div className="exercise-library-table" role="table" aria-label="Exercise Database">
            <div className="exercise-library-table__header" role="row"><span>Exercise</span><span>Body Part</span><span>Difficulty</span><span>Equipment</span><span>Status</span><span>Actions</span></div>
            {exercises.map((exercise) => (
              <div className={`exercise-library-table__row ${exercise.is_active ? '' : 'is-inactive'}`} role="row" key={exercise.exercise_id}>
                <strong>{exercise.exercise_name}</strong>
                <span>{exercise.body_part.name_en}</span>
                <span>{exercise.difficulty_level}</span>
                <span>{exercise.equipment}</span>
                <span>{exercise.is_active ? 'Active' : 'Inactive'}</span>
                <div>
                  <button type="button" aria-label={`修改 ${exercise.exercise_name}`} onClick={() => { setEditingId(exercise.exercise_id); setForm(formFromExercise(exercise)); setSaved('') }}><Edit3 size={17} /></button>
                  <button type="button" aria-label={`刪除 ${exercise.exercise_name}`} onClick={() => void deleteExercise(exercise)}><Trash2 size={17} /></button>
                </div>
              </div>
            ))}
          </div>
        </section>
      </section>
    </main>
  )
}
