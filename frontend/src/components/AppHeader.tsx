import { BarChart3, CalendarDays, Database, Dumbbell, History, LayoutDashboard, Play, UserRound, UsersRound } from 'lucide-react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { clearAdminToken, getAdminToken, getUserId } from '../lib/storage'
import { Brand } from './Brand'

const navigation = [
  { to: '/plan', label: '我的課表', icon: CalendarDays },
  { to: '/plan', label: '開始訓練', icon: Play },
  { to: '/history', label: '歷史紀錄', icon: History },
  { to: '/dashboard', label: 'Dashboard', icon: BarChart3 },
  { to: '/database', label: 'DB Schema', icon: Database },
  { to: '/profile', label: '編輯資料', icon: UserRound },
]

const adminNavigation = [
  { to: '/admin', label: 'Admin', icon: LayoutDashboard },
  { to: '/admin/users', label: 'Users', icon: UsersRound },
  { to: '/admin/statistics', label: 'Statistics', icon: BarChart3 },
  { to: '/admin/exercises', label: 'Exercises', icon: Dumbbell },
  { to: '/', label: 'Public Site', icon: Database },
]

export function AppHeader() {
  const location = useLocation()
  const navigate = useNavigate()
  const hasProfile = Boolean(getUserId())
  const hasAdminToken = Boolean(getAdminToken())
  const isAdminRoute = location.pathname.startsWith('/admin')
  const isAdminLogin = location.pathname === '/admin/login'
  const hiddenForWorkout = location.pathname.startsWith('/workout/')

  if (hiddenForWorkout) return null

  function logoutAdmin() {
    clearAdminToken()
    navigate('/admin/login')
  }

  return (
    <header className="app-header">
      <Link className="app-header__brand" to={isAdminRoute ? '/admin' : '/'}>
        <Brand />
      </Link>
      {isAdminRoute ? (
        <nav className="app-nav app-nav--admin" aria-label="管理後台導覽">
          {hasAdminToken && !isAdminLogin ? adminNavigation.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={label}
              to={to}
              end={to === '/admin'}
              className={({ isActive }) => `app-nav__link ${isActive ? 'is-active' : ''}`}
            >
              <Icon size={18} strokeWidth={1.9} aria-hidden="true" />
              <span>{label}</span>
            </NavLink>
          )) : (
            <NavLink to="/" className="app-nav__link">
              <Database size={18} strokeWidth={1.9} aria-hidden="true" />
              <span>Public Site</span>
            </NavLink>
          )}
          {hasAdminToken && !isAdminLogin ? (
            <button className="app-nav__button" type="button" onClick={logoutAdmin}>Logout</button>
          ) : null}
        </nav>
      ) : hasProfile ? (
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
