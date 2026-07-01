import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollReveal, revealDelay } from '@/components/ScrollReveal'
import { formatDate } from '@/lib/utils'

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
      <ScrollReveal>
        <Card>
          <CardContent className="py-12 text-center text-empty">{emptyMessage}</CardContent>
        </Card>
      </ScrollReveal>
    )
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {exercises.map((name, i) => (
        <ScrollReveal
          key={name}
          delay={revealDelay(i % 6, 90)}
          animation={i % 2 === 0 ? 'slide-left' : 'slide-right'}
        >
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">{name}</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={chartHeight}>
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
            </CardContent>
          </Card>
        </ScrollReveal>
      ))}
    </div>
  )
}
