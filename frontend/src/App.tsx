import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AppHeader } from './components/AppHeader'
import { LoadingScreen } from './components/LoadingScreen'

const HomePage = lazy(() => import('./pages/HomePage'))
const OnboardingPage = lazy(() => import('./pages/OnboardingPage'))
const PlanPage = lazy(() => import('./pages/PlanPage'))
const ActiveWorkoutPage = lazy(() => import('./pages/ActiveWorkoutPage'))
const HistoryPage = lazy(() => import('./pages/HistoryPage'))
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const ProfilePage = lazy(() => import('./pages/ProfilePage'))
const DatabaseSystemPage = lazy(() => import('./pages/DatabaseSystemPage'))
const AdminLoginPage = lazy(() => import('./pages/AdminLoginPage'))
const AdminDashboardPage = lazy(() => import('./pages/AdminDashboardPage'))
const AdminUsersPage = lazy(() => import('./pages/AdminUsersPage'))
const AdminUserDetailPage = lazy(() => import('./pages/AdminUserDetailPage'))
const AdminStatisticsPage = lazy(() => import('./pages/AdminStatisticsPage'))
const AdminExercisesPage = lazy(() => import('./pages/AdminExercisesPage'))

export default function App() {
  return (
    <div className="app-shell">
      <AppHeader />
      <Suspense fallback={<LoadingScreen label="載入中" />}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/onboarding" element={<OnboardingPage />} />
          <Route path="/plan" element={<PlanPage />} />
          <Route path="/workout/:planDayId" element={<ActiveWorkoutPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/database" element={<DatabaseSystemPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/admin/login" element={<AdminLoginPage />} />
          <Route path="/admin" element={<AdminDashboardPage />} />
          <Route path="/admin/users" element={<AdminUsersPage />} />
          <Route path="/admin/users/:userId" element={<AdminUserDetailPage />} />
          <Route path="/admin/statistics" element={<AdminStatisticsPage />} />
          <Route path="/admin/exercises" element={<AdminExercisesPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </div>
  )
}
