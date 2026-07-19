import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from '@/context/AuthContext'
import { Layout } from '@/components/Layout'
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { ForgotPasswordPage } from '@/pages/ForgotPasswordPage'
import { ResetPasswordPage } from '@/pages/ResetPasswordPage'
import { OnboardingPage } from '@/pages/OnboardingPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { WorkoutsPage } from '@/pages/WorkoutsPage'
import { WorkoutGraphPage } from '@/pages/WorkoutGraphPage'
import { DietPage } from '@/pages/DietPage'
import { BodyPage } from '@/pages/BodyPage'
import { RecoveryPage } from '@/pages/RecoveryPage'
import { CheckpointsPage } from '@/pages/CheckpointsPage'
import { CoachPage } from '@/pages/CoachPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="luxury-spinner" />
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  return <Layout>{children}</Layout>
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  const { pathname } = useLocation()
  if (loading) return null
  if (user && pathname !== '/register') return <Navigate to="/" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
          <Route path="/register" element={<PublicRoute><RegisterPage /></PublicRoute>} />
          <Route path="/forgot-password" element={<PublicRoute><ForgotPasswordPage /></PublicRoute>} />
          <Route path="/reset-password" element={<PublicRoute><ResetPasswordPage /></PublicRoute>} />
          <Route path="/onboarding" element={<ProtectedRoute><OnboardingPage /></ProtectedRoute>} />
          <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/workouts" element={<ProtectedRoute><WorkoutsPage /></ProtectedRoute>} />
          <Route path="/workout-graph" element={<ProtectedRoute><WorkoutGraphPage /></ProtectedRoute>} />
          <Route path="/diet" element={<ProtectedRoute><DietPage /></ProtectedRoute>} />
          <Route path="/body" element={<ProtectedRoute><BodyPage /></ProtectedRoute>} />
          <Route path="/recovery" element={<ProtectedRoute><RecoveryPage /></ProtectedRoute>} />
          <Route path="/checkpoints" element={<ProtectedRoute><CheckpointsPage /></ProtectedRoute>} />
          <Route path="/coach" element={<ProtectedRoute><CoachPage /></ProtectedRoute>} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
