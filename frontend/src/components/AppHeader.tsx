import { BarChart3, CalendarDays, Database, Dumbbell, History, LayoutDashboard, Play, UserRound, UsersRound } from 'lucide-react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useI18n } from '../i18n'
import { clearAdminToken, getAdminToken, getUserId } from '../lib/storage'
import { Brand } from './Brand'

const navigation = [
  { to: '/plan', labelKey: 'nav.plan', icon: CalendarDays },
  { to: '/plan', labelKey: 'nav.startWorkout', icon: Play },
  { to: '/history', labelKey: 'nav.history', icon: History },
  { to: '/dashboard', labelKey: 'nav.dashboard', icon: BarChart3 },
  { to: '/database', labelKey: 'nav.database', icon: Database },
  { to: '/profile', labelKey: 'nav.profile', icon: UserRound },
]

const adminNavigation = [
  { to: '/admin', labelKey: 'nav.admin', icon: LayoutDashboard },
  { to: '/admin/users', labelKey: 'nav.users', icon: UsersRound },
  { to: '/admin/statistics', labelKey: 'nav.statistics', icon: BarChart3 },
  { to: '/admin/exercises', labelKey: 'nav.exercises', icon: Dumbbell },
  { to: '/', labelKey: 'app.publicSite', icon: Database },
]

export function AppHeader() {
  const { language, setLanguage, t } = useI18n()
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

  const languageSwitch = (
    <label className="language-switch">
      <span>{t('app.language')}</span>
      <select
        aria-label={t('app.language')}
        value={language}
        onChange={(event) => setLanguage(event.target.value === 'en' ? 'en' : 'zh-TW')}
      >
        <option value="zh-TW">繁中</option>
        <option value="en">English</option>
      </select>
    </label>
  )

  return (
    <header className="app-header">
      <Link className="app-header__brand" to={isAdminRoute ? '/admin' : '/'}>
        <Brand />
      </Link>
      {isAdminRoute ? (
        <nav className="app-nav app-nav--admin" aria-label="管理後台導覽">
          {hasAdminToken && !isAdminLogin ? adminNavigation.map(({ to, labelKey, icon: Icon }) => (
            <NavLink
              key={labelKey}
              to={to}
              end={to === '/admin'}
              className={({ isActive }) => `app-nav__link ${isActive ? 'is-active' : ''}`}
            >
              <Icon size={18} strokeWidth={1.9} aria-hidden="true" />
              <span>{t(labelKey)}</span>
            </NavLink>
          )) : (
            <NavLink to="/" className="app-nav__link">
              <Database size={18} strokeWidth={1.9} aria-hidden="true" />
              <span>{t('app.publicSite')}</span>
            </NavLink>
          )}
          {hasAdminToken && !isAdminLogin ? (
            <button className="app-nav__button" type="button" onClick={logoutAdmin}>{t('nav.logout')}</button>
          ) : null}
          {languageSwitch}
        </nav>
      ) : hasProfile ? (
        <nav className="app-nav" aria-label="主要導覽">
          {navigation.map(({ to, labelKey, icon: Icon }) => (
            <NavLink
              key={labelKey}
              to={to}
              className={({ isActive }) =>
                `app-nav__link ${isActive && labelKey !== 'nav.startWorkout' ? 'is-active' : ''}`
              }
            >
              <Icon size={18} strokeWidth={1.9} aria-hidden="true" />
              <span>{t(labelKey)}</span>
            </NavLink>
          ))}
          {languageSwitch}
        </nav>
      ) : (
        <div className="header-actions">
          {languageSwitch}
          <Link className="header-cta" to="/onboarding">
            {t('nav.startNow')}
          </Link>
        </div>
      )}
    </header>
  )
}
