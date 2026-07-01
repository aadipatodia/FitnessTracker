import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  Dumbbell,
  UtensilsCrossed,
  Activity,
  Moon,
  Brain,
  LogOut,
  Menu,
  X,
  LineChart,
  Target,
  ListChecks,
} from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '@/context/AuthContext'
import { cn } from '@/lib/utils'
import { AmbientBackground } from '@/components/AmbientBackground'

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/workouts', label: 'Workouts', icon: Dumbbell },
  { path: '/workout-graph', label: 'Workout Graph', icon: LineChart },
  { path: '/diet', label: 'Diet', icon: UtensilsCrossed },
  { path: '/body', label: 'Body', icon: Activity },
  { path: '/recovery', label: 'Recovery', icon: Moon },
  { path: '/checkpoints', label: 'Checkpoints', icon: ListChecks },
  { path: '/coach', label: 'AI Coach', icon: Brain },
]

const mobileTabItems = [
  { path: '/', label: 'Home', icon: LayoutDashboard },
  { path: '/workouts', label: 'Workouts', icon: Dumbbell },
  { path: '/diet', label: 'Diet', icon: UtensilsCrossed },
  { path: '/coach', label: 'Coach', icon: Brain },
]

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const NavContent = () => (
    <>
      <div className="flex items-center gap-3 px-4 py-7 animate-slide-in-left">
        <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary/25 to-primary/5 ring-1 ring-primary/20 animate-pulse-gold">
          <Target className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h1 className="text-base font-bold gradient-text font-display">FitAI Coach</h1>
          <p className="text-[11px] uppercase tracking-[0.15em] text-muted-foreground">Elite Fitness</p>
        </div>
      </div>

      <nav className="flex-1 space-y-0.5 px-3">
        {navItems.map(({ path, label, icon: Icon }, i) => {
          const active = location.pathname === path
          return (
            <Link
              key={path}
              to={path}
              onClick={() => setMobileOpen(false)}
              style={{ animationDelay: `${i * 40}ms` }}
              className={cn(
                'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-300 animate-slide-in-left',
                active
                  ? 'nav-active-glow text-primary'
                  : 'text-muted-foreground hover:bg-secondary hover:text-foreground hover:translate-x-0.5'
              )}
            >
              <Icon className={cn('h-4 w-4 transition-transform duration-300', active && 'text-primary')} />
              {label}
            </Link>
          )
        })}
      </nav>

      <div className="border-t border-border/60 p-4">
        <div className="mb-3 rounded-xl bg-secondary/50 px-3 py-2.5 ring-1 ring-border/50">
          <p className="text-sm font-medium truncate">{user?.full_name}</p>
          <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
        </div>
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-sm text-muted-foreground hover:bg-secondary hover:text-foreground transition-all duration-300"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </>
  )

  return (
    <div className="relative flex min-h-screen bg-background">
      <AmbientBackground />

      {/* Desktop sidebar */}
      <aside className="relative z-10 hidden lg:flex lg:w-64 lg:flex-col lg:border-r lg:border-border/60 glass">
        <NavContent />
      </aside>

      {/* Mobile header */}
      <div className="relative z-10 flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-border/60 glass px-4 py-3 lg:hidden">
          <div className="flex items-center gap-2">
            <Target className="h-5 w-5 text-primary" />
            <span className="font-bold gradient-text font-display">FitAI Coach</span>
          </div>
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="rounded-lg p-2 transition-colors hover:bg-secondary"
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </header>

        {mobileOpen && (
          <div className="fixed inset-0 z-50 lg:hidden animate-fade-in">
            <div
              className="absolute inset-0 bg-black/70 backdrop-blur-sm"
              onClick={() => setMobileOpen(false)}
            />
            <aside className="absolute left-0 top-0 h-full w-64 glass border-r border-border/60 flex flex-col animate-slide-in-left">
              <NavContent />
            </aside>
          </div>
        )}

        <main className="relative flex-1 overflow-auto p-4 pb-20 md:p-6 md:pb-20 lg:p-8 lg:pb-8">
          {children}
        </main>

        <nav
          className="fixed inset-x-0 bottom-0 z-40 border-t border-border/60 glass pb-[env(safe-area-inset-bottom)] lg:hidden"
          aria-label="Primary navigation"
        >
          <div className="grid grid-cols-4">
            {mobileTabItems.map(({ path, label, icon: Icon }) => {
              const active = location.pathname === path
              return (
                <Link
                  key={path}
                  to={path}
                  className={cn(
                    'flex flex-col items-center justify-center gap-0.5 py-2.5 text-[10px] font-medium transition-all duration-300',
                    active
                      ? 'text-primary'
                      : 'text-muted-foreground hover:text-foreground'
                  )}
                >
                  <div className={cn(
                    'rounded-lg p-1 transition-all duration-300',
                    active && 'bg-primary/15 ring-1 ring-primary/25'
                  )}>
                    <Icon className="h-5 w-5" />
                  </div>
                  {label}
                </Link>
              )
            })}
          </div>
        </nav>
      </div>
    </div>
  )
}
