import { Link } from 'react-router-dom'
import {
  Target,
  Calendar,
  Scale,
  Percent,
  Dumbbell,
  Flame,
  Beef,
  ArrowRight,
  AlertTriangle,
} from 'lucide-react'
import { DashboardStats } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn, formatDate } from '@/lib/utils'

const GOAL_TYPE_LABELS: Record<string, string> = {
  reduce_body_fat: 'Reduce Body Fat',
  lose_fat_gain_muscle: 'Recomposition',
  increase_strength: 'Increase Strength',
  general_fitness: 'General Fitness',
}

function daysUntil(dateStr: string): number {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const deadline = new Date(dateStr + 'T00:00:00')
  return Math.ceil((deadline.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}

function displayDescription(description?: string): string | null {
  if (!description) return null
  const planIdx = description.indexOf('\n\n[Plan:')
  return planIdx >= 0 ? description.slice(0, planIdx).trim() : description.trim()
}

function MetricPair({
  label,
  current,
  target,
  unit,
  icon,
}: {
  label: string
  current?: number
  target?: number
  unit: string
  icon: React.ReactNode
}) {
  if (!target && !current) return null
  return (
    <div className="rounded-xl border border-border/60 bg-secondary/30 p-3 transition-all duration-300 hover:border-primary/20 hover:bg-secondary/50">
      <div className="flex items-center gap-1.5 text-xs uppercase tracking-wider text-muted-foreground">
        {icon}
        {label}
      </div>
      <p className="mt-1.5 text-sm font-medium font-display">
        {current != null ? `${current}${unit}` : '—'}
        {target != null && (
          <span className="text-muted-foreground"> → {target}{unit}</span>
        )}
      </p>
    </div>
  )
}

export function GoalSection({ stats }: { stats: DashboardStats | null }) {
  const goal = stats?.active_goal

  if (!goal) {
    return (
      <Card className="border-primary/25 bg-gradient-to-br from-primary/8 via-transparent to-transparent overflow-hidden">
        <CardContent className="flex flex-col items-center gap-4 py-10 text-center sm:flex-row sm:justify-between sm:text-left">
          <div className="flex flex-col items-center gap-3 sm:flex-row sm:items-start">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-primary/25 to-primary/5 ring-1 ring-primary/20 animate-pulse-gold">
              <Target className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h2 className="text-lg font-semibold">Set your fitness goal</h2>
              <p className="mt-1 text-sm text-muted-foreground max-w-md">
                Define your end goal, set a deadline, and get AI-guided coaching tailored to what you want to achieve.
              </p>
            </div>
          </div>
          <Link
            to="/onboarding"
            className={cn(
              'inline-flex items-center justify-center gap-2 font-medium transition-all',
              'btn-luxury h-10 px-4 text-sm rounded-xl',
            )}
          >
            Set a goal
            <ArrowRight className="h-4 w-4" />
          </Link>
        </CardContent>
      </Card>
    )
  }

  const description = displayDescription(goal.description)
  const daysLeft = goal.target_date ? daysUntil(goal.target_date) : null
  const isOverdue = daysLeft != null && daysLeft < 0
  const progress = stats?.goal_progress_percent ?? 0

  const showBodyFat =
    goal.goal_type === 'reduce_body_fat' || goal.goal_type === 'lose_fat_gain_muscle'
  const showWeight = goal.goal_type !== 'increase_strength'
  const showStrength = goal.goal_type === 'increase_strength'

  const currentWeight = stats?.current_weight ?? goal.current_weight
  const currentBodyFat = stats?.current_body_fat ?? goal.current_body_fat

  return (
    <Card className="border-primary/25">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle className="text-lg">{goal.title}</CardTitle>
              <span className="rounded-full bg-primary/15 px-2.5 py-0.5 text-xs font-medium text-primary ring-1 ring-primary/20">
                {GOAL_TYPE_LABELS[goal.goal_type] ?? goal.goal_type}
              </span>
            </div>
            {description && (
              <p className="text-sm text-muted-foreground">{description}</p>
            )}
          </div>
          <Link to="/onboarding">
            <Button variant="outline" size="sm">Update goal</Button>
          </Link>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {goal.target_date && (
          <div
            className={`flex items-center gap-2 text-sm ${
              isOverdue ? 'text-amber-400' : 'text-muted-foreground'
            }`}
          >
            {isOverdue ? (
              <AlertTriangle className="h-4 w-4 shrink-0" />
            ) : (
              <Calendar className="h-4 w-4 shrink-0" />
            )}
            <span>
              Deadline: {formatDate(goal.target_date)}
              {daysLeft != null && (
                <>
                  {' · '}
                  {isOverdue
                    ? `${Math.abs(daysLeft)} day${Math.abs(daysLeft) !== 1 ? 's' : ''} overdue`
                    : daysLeft === 0
                      ? 'Due today'
                      : `${daysLeft} day${daysLeft !== 1 ? 's' : ''} left`}
                </>
              )}
            </span>
          </div>
        )}

        <div>
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="text-muted-foreground">Overall progress</span>
            <span className="font-medium text-primary">{progress}%</span>
          </div>
          <div className="luxury-progress h-2.5">
            <div
              className="luxury-progress-fill"
              style={{ width: `${Math.min(100, progress)}%` }}
            />
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {showWeight && (
            <MetricPair
              label="Weight"
              current={currentWeight}
              target={goal.target_weight}
              unit=" kg"
              icon={<Scale className="h-3 w-3" />}
            />
          )}
          {showBodyFat && (
            <MetricPair
              label="Body fat"
              current={currentBodyFat}
              target={goal.target_body_fat}
              unit="%"
              icon={<Percent className="h-3 w-3" />}
            />
          )}
          {showStrength && goal.target_exercise && (
            <MetricPair
              label={goal.target_exercise}
              current={undefined}
              target={goal.target_weight_lifted}
              unit=" kg"
              icon={<Dumbbell className="h-3 w-3" />}
            />
          )}
          {goal.target_calories != null && (
            <div className="rounded-xl border border-border/60 bg-secondary/30 p-3 transition-all duration-300 hover:border-primary/20">
              <div className="flex items-center gap-1.5 text-xs uppercase tracking-wider text-muted-foreground">
                <Flame className="h-3 w-3" />
                Calories today
              </div>
              <p className="mt-1.5 text-sm font-medium font-display">
                {Math.round(stats?.calories_today ?? 0)}
                <span className="text-muted-foreground"> / {goal.target_calories} target</span>
              </p>
              {(stats?.calories_burned_today ?? 0) > 0 && (
                <p className="mt-1 text-xs text-muted-foreground">
                  ~{Math.round(stats?.calories_burned_today ?? 0)} kcal burned today · net{' '}
                  {Math.round((stats?.calories_today ?? 0) - (stats?.calories_burned_today ?? 0))} kcal
                </p>
              )}
            </div>
          )}
          {goal.target_protein != null && (
            <div className="rounded-xl border border-border/60 bg-secondary/30 p-3 transition-all duration-300 hover:border-primary/20">
              <div className="flex items-center gap-1.5 text-xs uppercase tracking-wider text-muted-foreground">
                <Beef className="h-3 w-3" />
                Protein today
              </div>
              <p className="mt-1.5 text-sm font-medium font-display">
                {Math.round(stats?.protein_today ?? 0)}g
                <span className="text-muted-foreground"> / {goal.target_protein}g target</span>
              </p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
