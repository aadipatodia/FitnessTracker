import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDate } from '@/lib/utils'

const CHART_COLORS = ['#f59e0b', '#22c55e', '#6366f1', '#ec4899', '#14b8a6', '#f97316', '#8b5cf6']

export interface StrengthProgressPoint {
  date: string
  exercise: string
  max_weight: number
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

const tooltipStyle = { background: '#12121a', border: '1px solid #27272a', borderRadius: 8 }

export function ExerciseProgressCharts({
  strengthProgression,
  chartHeight = 220,
  emptyMessage = 'Log workouts to see exercise progress.',
}: {
  strengthProgression: StrengthProgressPoint[]
  chartHeight?: number
  emptyMessage?: string
}) {
  const byExercise = groupStrengthByExercise(strengthProgression)
  const exercises = Object.keys(byExercise).sort((a, b) => a.localeCompare(b))

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
            <CardTitle className="text-base">{name}</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={chartHeight}>
              <LineChart data={byExercise[name]}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="date" tickFormatter={(d) => formatDate(d)} stroke="#71717a" fontSize={11} />
                <YAxis stroke="#71717a" fontSize={11} unit=" kg" domain={['auto', 'auto']} />
                <Tooltip
                  contentStyle={tooltipStyle}
                  labelFormatter={(d) => formatDate(d)}
                  formatter={(value) => [`${value} kg`, 'Max weight']}
                />
                <Line
                  type="monotone"
                  dataKey="max_weight"
                  stroke={CHART_COLORS[i % CHART_COLORS.length]}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
