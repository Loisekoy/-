import { BarChart3, BookOpen, CalendarDays, Database, History, Play, UserRound } from 'lucide-react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { getUserId } from '../lib/storage'
import { Brand } from './Brand'

const navigation = [
  { to: '/plan', label: '我的課表', icon: CalendarDays },
  { to: '/plan', label: '開始訓練', icon: Play },
  { to: '/history', label: '歷史紀錄', icon: History },
  { to: '/dashboard', label: 'Dashboard', icon: BarChart3 },
  { to: '/exercises', label: '動作資料庫', icon: BookOpen },
  { to: '/database', label: 'DB Schema', icon: Database },
  { to: '/profile', label: '編輯資料', icon: UserRound },
]

export function AppHeader() {
  const location = useLocation()
  const hasProfile = Boolean(getUserId())
  const hiddenForWorkout = location.pathname.startsWith('/workout/')

  if (hiddenForWorkout) return null

  return (
    <header className="app-header">
      <Link className="app-header__brand" to="/">
        <Brand />
      </Link>
      {hasProfile ? (
        <nav className="app-nav" aria-label="主要導覽">
          {navigation.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={label}
              to={to}
              className={({ isActive }) =>
                `app-nav__link ${isActive && label !== '開始訓練' ? 'is-active' : ''}`
              }
            >
              <Icon size={18} strokeWidth={1.9} aria-hidden="true" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
      ) : (
        <Link className="header-cta" to="/onboarding">
          從現在開始
        </Link>
      )}
    </header>
  )
}
