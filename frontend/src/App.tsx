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
const ExerciseLibraryPage = lazy(() => import('./pages/ExerciseLibraryPage'))
const DatabaseSystemPage = lazy(() => import('./pages/DatabaseSystemPage'))

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
          <Route path="/exercises" element={<ExerciseLibraryPage />} />
          <Route path="/database" element={<DatabaseSystemPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </div>
  )
}
