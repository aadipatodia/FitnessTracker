import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { KeyRound, Target } from 'lucide-react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input, Label } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { AmbientBackground } from '@/components/AmbientBackground'

type Step = 'request' | 'reset' | 'done'

export function ResetPasswordPage() {
  const [step, setStep] = useState<Step>('request')
  const [email, setEmail] = useState('')
  const [resetToken, setResetToken] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleRequestReset = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.requestPasswordReset(email)
      if (res.reset_token) {
        setResetToken(res.reset_token)
      }
      setStep('reset')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to request password reset')
    } finally {
      setLoading(false)
    }
  }

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    setLoading(true)
    try {
      await api.resetPassword({
        email,
        reset_token: resetToken,
        new_password: newPassword,
      })
      setStep('done')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-bg relative flex min-h-screen items-center justify-center p-4">
      <AmbientBackground />
      <div className="auth-grid" aria-hidden="true" />

      <div className="relative z-10 w-full max-w-md">
        <div className="mb-10 text-center animate-fade-up">
          <div className="relative mx-auto mb-5 flex h-16 w-16 items-center justify-center">
            <div className="absolute inset-0 rounded-2xl bg-primary/20 blur-xl animate-pulse-gold" />
            <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/30 to-primary/5 ring-1 ring-primary/30">
              <Target className="h-8 w-8 text-primary" />
            </div>
          </div>
          <h1 className="text-4xl font-bold gradient-text font-display">FitAI Coach</h1>
          <p className="mt-3 text-body-secondary">Reset your account password</p>
        </div>

        <Card className="animate-fade-up stagger-2 border-primary/20">
          <CardHeader>
            <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <KeyRound className="h-5 w-5 text-primary" />
            </div>
            <CardTitle>
              {step === 'request' && 'Forgot password'}
              {step === 'reset' && 'Set new password'}
              {step === 'done' && 'Password updated'}
            </CardTitle>
            <CardDescription>
              {step === 'request' && 'Enter your email to receive a reset token'}
              {step === 'reset' && 'Enter the reset token and choose a new password'}
              {step === 'done' && 'Your password has been changed successfully'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {step === 'request' && (
              <form onSubmit={handleRequestReset} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
                {error && <p className="text-sm text-destructive">{error}</p>}
                <Button type="submit" className="w-full" disabled={loading}>
                  {loading ? 'Generating token...' : 'Get reset token'}
                </Button>
              </form>
            )}

            {step === 'reset' && (
              <form onSubmit={handleResetPassword} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="reset-email">Email</Label>
                  <Input
                    id="reset-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="reset-token">Reset token</Label>
                  <Input
                    id="reset-token"
                    value={resetToken}
                    onChange={(e) => setResetToken(e.target.value)}
                    placeholder="Paste your reset token"
                    required
                  />
                  <p className="text-meta">
                    Token expires in 15 minutes. In production this would be sent by email.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="new-password">New password</Label>
                  <Input
                    id="new-password"
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    minLength={6}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirm-password">Confirm password</Label>
                  <Input
                    id="confirm-password"
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    minLength={6}
                    required
                  />
                </div>
                {error && <p className="text-sm text-destructive">{error}</p>}
                <Button type="submit" className="w-full" disabled={loading}>
                  {loading ? 'Resetting...' : 'Reset password'}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  className="w-full"
                  onClick={() => {
                    setStep('request')
                    setError('')
                  }}
                >
                  Request a new token
                </Button>
              </form>
            )}

            {step === 'done' && (
              <div className="space-y-4">
                <p className="text-body-secondary">
                  You can now sign in with your new password.
                </p>
                <Button className="w-full" onClick={() => navigate('/login')}>
                  Go to sign in
                </Button>
              </div>
            )}

            {step !== 'done' && (
              <p className="mt-4 text-center text-meta">
                Remember your password?{' '}
                <Link to="/login" className="text-primary hover:text-accent transition-colors font-medium">
                  Sign in
                </Link>
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
