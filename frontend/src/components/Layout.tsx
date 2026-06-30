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
} from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '@/context/AuthContext'
import { cn } from '@/lib/utils'

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/workouts', label: 'Workouts', icon: Dumbbell },
  { path: '/workout-graph', label: 'Workout Graph', icon: LineChart },
  { path: '/diet', label: 'Diet', icon: UtensilsCrossed },
  { path: '/body', label: 'Body', icon: Activity },
  { path: '/recovery', label: 'Recovery', icon: Moon },
  { path: '/coach', label: 'AI Coach', icon: Brain },
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
      <div className="flex items-center gap-2 px-4 py-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/20">
          <Target className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h1 className="text-base font-bold gradient-text">FitAI Coach</h1>
          <p className="text-xs text-muted-foreground">AI Fitness Platform</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {navItems.map(({ path, label, icon: Icon }) => (
          <Link
            key={path}
            to={path}
            onClick={() => setMobileOpen(false)}
            className={cn(
              'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
              location.pathname === path
                ? 'bg-primary/10 text-primary'
                : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </Link>
        ))}
      </nav>

      <div className="border-t border-border p-4">
        <div className="mb-3 px-1">
          <p className="text-sm font-medium truncate">{user?.full_name}</p>
          <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
        </div>
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </>
  )

  return (
    <div className="flex min-h-screen bg-background">
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex lg:w-64 lg:flex-col lg:border-r lg:border-border lg:bg-card">
        <NavContent />
      </aside>

      {/* Mobile header */}
      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-border bg-card px-4 py-3 lg:hidden">
          <div className="flex items-center gap-2">
            <Target className="h-5 w-5 text-primary" />
            <span className="font-bold gradient-text">FitAI Coach</span>
          </div>
          <button onClick={() => setMobileOpen(!mobileOpen)} className="p-2">
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </header>

        {mobileOpen && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <div className="absolute inset-0 bg-black/60" onClick={() => setMobileOpen(false)} />
            <aside className="absolute left-0 top-0 h-full w-64 bg-card border-r border-border flex flex-col">
              <NavContent />
            </aside>
          </div>
        )}

        <main className="flex-1 overflow-auto p-4 md:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  )
}
