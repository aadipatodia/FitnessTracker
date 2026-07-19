import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Target, Sparkles } from 'lucide-react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input, Label } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { AmbientBackground } from '@/components/AmbientBackground'

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.forgotPassword(email)
      setMessage(res.message)
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
            Reset your password
          </p>
        </div>

        <Card className="animate-fade-up stagger-2 border-primary/20">
          <CardHeader>
            <CardTitle>Forgot password</CardTitle>
            <CardDescription>Enter your email and we'll send you a reset link</CardDescription>
          </CardHeader>
          <CardContent>
            {message ? (
              <p className="text-sm text-body-secondary animate-fade-in">{message}</p>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
                </div>
                {error && <p className="text-sm text-destructive animate-fade-in">{error}</p>}
                <Button type="submit" className="w-full" disabled={loading}>
                  {loading ? 'Sending...' : 'Send reset link'}
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
