import { Image as ImageIcon, Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, adminRequest, apiRequest } from '../api/client'
import type { BodyPart, Exercise } from '../api/types'
import { ErrorNotice } from '../components/ErrorNotice'
import { LoadingScreen } from '../components/LoadingScreen'
import {
  getExerciseImageSrc,
  getExerciseInstructions,
  getPrimaryMuscles,
} from '../lib/exerciseGuidance'
import { clearAdminToken, getAdminToken } from '../lib/storage'

export default function AdminExercisesPage() {
  const navigate = useNavigate()
  const [bodyParts, setBodyParts] = useState<BodyPart[]>([])
  const [exercises, setExercises] = useState<Exercise[]>([])
  const [search, setSearch] = useState('')
  const [bodyPartId, setBodyPartId] = useState('')
  const [equipment, setEquipment] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const queryString = useMemo(() => {
    const params = new URLSearchParams()
    if (search.trim()) params.set('search', search.trim())
    if (bodyPartId) params.set('body_part_id', bodyPartId)
    if (equipment.trim()) params.set('equipment', equipment.trim())
    const suffix = params.toString()
    return suffix ? `?${suffix}` : ''
  }, [bodyPartId, equipment, search])

  useEffect(() => {
    apiRequest<BodyPart[]>('/reference/body-parts')
      .then(setBodyParts)
      .catch(() => setBodyParts([]))
  }, [])

  useEffect(() => {
    if (!getAdminToken()) {
      navigate('/admin/login', { replace: true })
      return
    }
    let active = true
    adminRequest<Exercise[]>(`/admin/exercises${queryString}`)
      .then((payload) => {
        if (!active) return
        setExercises(payload)
        setError('')
      })
      .catch((reason) => {
        if (!active) return
        if (reason instanceof ApiError && reason.status === 401) {
          clearAdminToken()
          navigate('/admin/login', { replace: true })
          return
        }
        setError(reason instanceof Error ? reason.message : '無法載入 Exercise Database。')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [navigate, queryString])

  return (
    <main className="page admin-page">
      <header className="page-heading admin-heading">
        <div>
          <h1>Exercise Database</h1>
          <p>後台查看 Exercise 圖片/GIF、主要肌群、輔助肌群與動作步驟。公開使用者不能修改這些資料。</p>
        </div>
      </header>
      {error ? <ErrorNotice message={error} /> : null}

      <section className="admin-card">
        <div className="admin-filter-bar">
          <label className="search-field">
            <Search size={18} />
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜尋 Bench、Squat、Cable..." />
          </label>
          <label>
            <span>Body Part</span>
            <select value={bodyPartId} onChange={(event) => setBodyPartId(event.target.value)}>
              <option value="">全部部位</option>
              {bodyParts.map((part) => (
                <option key={part.body_part_id} value={part.body_part_id}>
                  {part.name_en} {part.name_zh}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Equipment</span>
            <input value={equipment} onChange={(event) => setEquipment(event.target.value)} placeholder="Barbell, Cable..." />
          </label>
        </div>
      </section>

      {loading ? <LoadingScreen label="正在載入 Exercises" /> : (
        <section className="admin-exercise-grid" aria-label="Admin exercise database">
          {exercises.length ? exercises.map((exercise) => {
            const instructions = getExerciseInstructions(exercise)
            return (
              <article className="admin-exercise-card" key={exercise.exercise_id}>
                <div className="admin-exercise-card__media">
                  <img src={getExerciseImageSrc(exercise)} alt={`${exercise.exercise_name} 示範`} />
                  <span><ImageIcon size={15} />{exercise.gif_url ? 'ExerciseDB GIF' : 'Local fallback'}</span>
                </div>
                <div className="admin-exercise-card__body">
                  <div className="exercise-card-heading">
                    <div>
                      <span>{exercise.body_part.name_en} / {exercise.body_part.name_zh}</span>
                      <h2>{exercise.exercise_name}</h2>
                    </div>
                    <div className="exercise-tags">
                      <span>{exercise.difficulty_level}</span>
                      <span>{exercise.equipment}</span>
                      <span>{exercise.movement_type}</span>
                    </div>
                  </div>
                  <p className="exercise-description">{exercise.description}</p>
                  <div className="exercise-muscle-grid">
                    <div>
                      <span>Target Muscles</span>
                      <p>{getPrimaryMuscles(exercise).join(', ')}</p>
                    </div>
                    <div>
                      <span>Secondary Muscles</span>
                      <p>{exercise.secondary_muscles.length ? exercise.secondary_muscles.join(', ') : '—'}</p>
                    </div>
                  </div>
                  <ol className="admin-instruction-list">
                    {instructions.slice(0, 5).map((instruction) => (
                      <li key={instruction}>{instruction}</li>
                    ))}
                  </ol>
                </div>
              </article>
            )
          }) : <p className="admin-empty">沒有符合條件的 exercises。</p>}
        </section>
      )}
    </main>
  )
}
