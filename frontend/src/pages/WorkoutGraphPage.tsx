import { useEffect, useState } from 'react'
import { api, DashboardCharts } from '@/lib/api'
import { ExerciseProgressCharts } from '@/components/ExerciseProgressCharts'
import { PageHeader } from '@/components/PageHeader'
import { Card, CardContent } from '@/components/ui/card'

const PERIOD_OPTIONS = [
  { label: 'Last 30 days', value: 30 },
  { label: 'Last 90 days', value: 90 },
  { label: 'Last year', value: 365 },
  { label: 'All time', value: 0 },
]

export function WorkoutGraphPage() {
  const [days, setDays] = useState(365)
  const [charts, setCharts] = useState<DashboardCharts | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    api.getCharts(days)
      .then(setCharts)
      .catch((err) => {
        console.error(err)
        setError(err instanceof Error ? err.message : 'Failed to load workout graphs')
        setCharts(null)
      })
      .finally(() => setLoading(false))
  }, [days])

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between">
        <PageHeader
          title="Workout Graph"
          subtitle="Max weight per session with coaching on where you are and what to hit next"
        />
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="w-full rounded-xl border border-border bg-muted/50 px-3 py-2.5 text-base text-foreground transition-all focus:outline-none focus:ring-2 focus:ring-primary/40 sm:w-auto"
        >
          {PERIOD_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center gap-3 h-64">
          <div className="luxury-spinner" />
          <p className="text-sm text-muted-foreground">Loading workout progress…</p>
        </div>
      ) : error ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-destructive">{error}</p>
            <p className="mt-2 text-sm text-muted-foreground">
              Check that the backend is running, then refresh this page.
            </p>
          </CardContent>
        </Card>
      ) : (
        <ExerciseProgressCharts
          strengthProgression={charts?.strength_progression ?? []}
          exerciseAssessments={charts?.exercise_assessments ?? []}
          chartHeight={280}
          emptyMessage="No workout data yet. Log a workout to see your progress graphs."
        />
      )}
    </div>
  )
}
