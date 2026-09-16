import { Filter, Search, SlidersHorizontal } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError, adminRequest, apiRequest } from '../api/client'
import type { PaginatedAdminUsers, TrainingGoal } from '../api/types'
import { ErrorNotice } from '../components/ErrorNotice'
import { LoadingScreen } from '../components/LoadingScreen'
import { parseApiDate } from '../lib/datetime'
import { clearAdminToken, getAdminToken } from '../lib/storage'

export default function AdminUsersPage() {
  const navigate = useNavigate()
  const [goals, setGoals] = useState<TrainingGoal[]>([])
  const [users, setUsers] = useState<PaginatedAdminUsers | null>(null)
  const [search, setSearch] = useState('')
  const [goalId, setGoalId] = useState('')
  const [experience, setExperience] = useState('')
  const [sort, setSort] = useState('created_desc')
  const [page, setPage] = useState(1)
  const [error, setError] = useState('')

  const queryString = useMemo(() => {
    const params = new URLSearchParams()
    if (search.trim()) params.set('search', search.trim())
    if (goalId) params.set('training_goal_id', goalId)
    if (experience) params.set('experience', experience)
    params.set('sort', sort)
    params.set('page', String(page))
    params.set('page_size', '10')
    return `?${params.toString()}`
  }, [experience, goalId, page, search, sort])

  useEffect(() => {
    apiRequest<TrainingGoal[]>('/reference/training-goals')
      .then(setGoals)
      .catch(() => setGoals([]))
  }, [])

  useEffect(() => {
    if (!getAdminToken()) {
      navigate('/admin/login', { replace: true })
      return
    }
    let active = true
    adminRequest<PaginatedAdminUsers>(`/admin/users${queryString}`)
      .then((payload) => {
        if (active) {
          setUsers(payload)
          setError('')
        }
      })
      .catch((reason) => {
        if (!active) return
        if (reason instanceof ApiError && reason.status === 401) {
          clearAdminToken()
          navigate('/admin/login', { replace: true })
          return
        }
        setError(reason instanceof Error ? reason.message : '無法載入 Users。')
      })
    return () => {
      active = false
    }
  }, [navigate, queryString])

  const totalPages = users ? Math.max(1, Math.ceil(users.total / users.page_size)) : 1

  if (!users && !error) return <LoadingScreen label="正在載入 Users" />

  return (
    <main className="page admin-page">
      <header className="page-heading admin-heading">
        <div>
          <h1>Users</h1>
          <p>管理者可查看所有使用者資料，支援搜尋、Training Goal / Experience 篩選、排序與分頁。</p>
        </div>
      </header>
      {error ? <ErrorNotice message={error} /> : null}

      <section className="admin-card">
        <div className="admin-filter-bar">
          <label className="search-field">
            <Search size={18} />
            <input
              value={search}
              onChange={(event) => {
                setSearch(event.target.value)
                setPage(1)
              }}
              placeholder="搜尋 name 或 user_id"
            />
          </label>
          <label>
            <span><Filter size={16} />Training Goal</span>
            <select
              value={goalId}
              onChange={(event) => {
                setGoalId(event.target.value)
                setPage(1)
              }}
            >
              <option value="">全部目標</option>
              {goals.map((goal) => (
                <option key={goal.training_goal_id} value={goal.training_goal_id}>
                  {goal.goal_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Experience</span>
            <select
              value={experience}
              onChange={(event) => {
                setExperience(event.target.value)
                setPage(1)
              }}
            >
              <option value="">全部程度</option>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </label>
          <label>
            <span><SlidersHorizontal size={16} />Sort</span>
            <select value={sort} onChange={(event) => setSort(event.target.value)}>
              <option value="created_desc">Newest first</option>
              <option value="created_asc">Oldest first</option>
              <option value="name_asc">Name A-Z</option>
              <option value="age_desc">Age high-low</option>
              <option value="age_asc">Age low-high</option>
            </select>
          </label>
        </div>
      </section>

      <section className="admin-card admin-card--table">
        <div className="section-heading">
          <h2>All Users</h2>
          <p>{users?.total ?? 0} records</p>
        </div>
        {users?.items.length ? (
          <div className="admin-users-table" role="table" aria-label="Users table">
            <div className="admin-users-table__header" role="row">
              <span>Name</span>
              <span>Goal</span>
              <span>Experience</span>
              <span>Schedule</span>
              <span>Body Parts</span>
              <span>Created</span>
            </div>
            {users.items.map((user) => (
              <Link className="admin-users-table__row" role="row" to={`/admin/users/${user.user_id}`} key={user.user_id}>
                <div>
                  <strong>{user.name}</strong>
                  <small>{user.gender ?? 'not specified'}・{user.age} yrs・{user.height_cm} cm・{user.latest_weight_kg ?? '—'} kg</small>
                </div>
                <span>{user.training_goal}</span>
                <span>{user.training_experience}</span>
                <span>{user.training_days_per_week} days / {user.training_duration_minutes} min</span>
                <span>{user.preferred_body_parts.join(', ')}</span>
                <time>{parseApiDate(user.created_at).toLocaleDateString('zh-TW')}</time>
              </Link>
            ))}
          </div>
        ) : (
          <p className="admin-empty">目前沒有符合條件的使用者。</p>
        )}
        <div className="admin-pagination">
          <button
            className="button button--secondary"
            type="button"
            disabled={page <= 1}
            onClick={() => setPage((current) => Math.max(1, current - 1))}
          >
            上一頁
          </button>
          <span>Page {page} / {totalPages}</span>
          <button
            className="button button--secondary"
            type="button"
            disabled={page >= totalPages}
            onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
          >
            下一頁
          </button>
        </div>
      </section>
    </main>
  )
}
