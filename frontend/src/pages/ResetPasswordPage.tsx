import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Target, Sparkles } from 'lucide-react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input, Label } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { AmbientBackground } from '@/components/AmbientBackground'

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }
    setLoading(true)
    try {
      await api.resetPassword(token, password)
      navigate('/login')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
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
          <p className="mt-3 flex items-center justify-center gap-1.5 text-body-secondary">
            <Sparkles className="h-3.5 w-3.5 text-primary/70" />
            Choose a new password
          </p>
        </div>

        <Card className="animate-fade-up stagger-2 border-primary/20">
          <CardHeader>
            <CardTitle>Reset password</CardTitle>
            <CardDescription>Enter a new password for your account</CardDescription>
          </CardHeader>
          <CardContent>
            {!token ? (
              <p className="text-sm text-destructive">
                This reset link is missing its token. Please use the link from your email.
              </p>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="password">New password</Label>
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    minLength={6}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirm password</Label>
                  <Input
                    id="confirmPassword"
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    minLength={6}
                    required
                  />
                </div>
                {error && <p className="text-sm text-destructive animate-fade-in">{error}</p>}
                <Button type="submit" className="w-full" disabled={loading}>
                  {loading ? 'Updating...' : 'Update password'}
                </Button>
              </form>
            )}
            <p className="mt-5 text-center text-meta">
              <Link to="/login" className="text-primary hover:text-accent transition-colors font-medium">
                Back to sign in
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
