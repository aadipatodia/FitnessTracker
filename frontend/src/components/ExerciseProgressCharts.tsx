import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { Target, TrendingDown, TrendingUp, Minus, Sparkles } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDate } from '@/lib/utils'
import type { ExerciseAssessment } from '@/lib/api'

const CHART_COLORS = ['#c9a962', '#e8d5b5', '#a8893a', '#d4b872', '#8a7140', '#f5e6c8', '#b8954a']
const CHART_GRID = 'rgba(201, 169, 98, 0.08)'
const CHART_AXIS = '#c4b89a'
const tooltipStyle = {
  background: 'rgba(16, 14, 12, 0.95)',
  border: '1px solid rgba(201, 169, 98, 0.2)',
  borderRadius: 12,
}

export interface StrengthProgressPoint {
  date: string
  exercise: string
  max_weight: number
}

const TREND_CONFIG = {
  improving: {
    label: 'Progressing',
    icon: TrendingUp,
    className: 'text-emerald-400/90 bg-emerald-500/10 border-emerald-500/20',
  },
  plateau: {
    label: 'Plateau',
    icon: Minus,
    className: 'text-amber-400/90 bg-amber-500/10 border-amber-500/20',
  },
  declining: {
    label: 'Below recent best',
    icon: TrendingDown,
    className: 'text-rose-400/90 bg-rose-500/10 border-rose-500/20',
  },
  new: {
    label: 'New baseline',
    icon: Sparkles,
    className: 'text-primary/90 bg-primary/10 border-primary/20',
  },
} as const

type TrendKey = keyof typeof TREND_CONFIG

function normalizeTrend(trend: string): TrendKey {
  if (trend in TREND_CONFIG) return trend as TrendKey
  return 'plateau'
}

export function groupStrengthByExercise(
  points: StrengthProgressPoint[],
): Record<string, { date: string; max_weight: number }[]> {
  const byExercise: Record<string, { date: string; max_weight: number }[]> = {}
  for (const p of points) {
    if (!byExercise[p.exercise]) byExercise[p.exercise] = []
    byExercise[p.exercise].push({ date: p.date, max_weight: p.max_weight })
  }
  for (const name of Object.keys(byExercise)) {
    byExercise[name].sort((a, b) => a.date.localeCompare(b.date))
  }
  return byExercise
}

function ExerciseAssessmentPanel({ assessment }: { assessment: ExerciseAssessment }) {
  const trend = TREND_CONFIG[normalizeTrend(assessment.trend)]
  const TrendIcon = trend.icon

  return (
    <div className="mt-4 space-y-3 border-t border-border/60 pt-4">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${trend.className}`}
        >
          <TrendIcon className="h-3.5 w-3.5" />
          {trend.label}
        </span>
        {assessment.is_goal_exercise && (
          <span className="inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">
            Goal lift
            {assessment.goal_lift_progress_percent != null && (
              <span className="text-primary/80">· {assessment.goal_lift_progress_percent}%</span>
            )}
          </span>
        )}
      </div>

      <p className="text-sm leading-relaxed text-muted-foreground">{assessment.status_summary}</p>

      <div className="rounded-xl border border-primary/20 bg-primary/5 px-3 py-2.5">
        <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-primary/80">
          <Target className="h-3.5 w-3.5" />
          Next session
        </div>
        <p className="text-sm leading-relaxed text-foreground">{assessment.next_session_summary}</p>
      </div>

      {assessment.goal_note && (
        <p className="text-xs leading-relaxed text-muted-foreground/90">{assessment.goal_note}</p>
      )}
    </div>
  )
}

export function ExerciseProgressCharts({
  strengthProgression,
  exerciseAssessments = [],
  chartHeight = 220,
  emptyMessage = 'Log workouts to see exercise progress.',
}: {
  strengthProgression: StrengthProgressPoint[]
  exerciseAssessments?: ExerciseAssessment[]
  chartHeight?: number
  emptyMessage?: string
}) {
  const byExercise = groupStrengthByExercise(strengthProgression)
  const exercises = Object.keys(byExercise).sort((a, b) => a.localeCompare(b))
  const assessmentByExercise = Object.fromEntries(
    exerciseAssessments.map((a) => [a.exercise, a]),
  )

  if (exercises.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">{emptyMessage}</CardContent>
      </Card>
    )
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {exercises.map((name, i) => (
        <Card key={name}>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">{name}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="w-full" style={{ height: chartHeight }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={byExercise[name]}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
                  <XAxis dataKey="date" tickFormatter={(d) => formatDate(d)} stroke={CHART_AXIS} fontSize={13} tick={{ fill: CHART_AXIS }} />
                  <YAxis stroke={CHART_AXIS} fontSize={13} tick={{ fill: CHART_AXIS }} unit=" kg" domain={['auto', 'auto']} />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    labelFormatter={(d) => formatDate(d)}
                    formatter={(value) => [`${value} kg`, 'Max weight']}
                  />
                  <Line
                    type="monotone"
                    dataKey="max_weight"
                    stroke={CHART_COLORS[i % CHART_COLORS.length]}
                    strokeWidth={2.5}
                    dot={{ r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            {assessmentByExercise[name] && (
              <ExerciseAssessmentPanel assessment={assessmentByExercise[name]} />
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
