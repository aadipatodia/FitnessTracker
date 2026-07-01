import { useEffect, useState } from 'react'
import { api, DashboardCharts } from '@/lib/api'
import { ExerciseProgressCharts } from '@/components/ExerciseProgressCharts'
import { PageHeader } from '@/components/PageHeader'
import { ScrollReveal } from '@/components/ScrollReveal'

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

  useEffect(() => {
    setLoading(true)
    api.getCharts(days)
      .then(setCharts)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [days])

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between">
        <PageHeader
          title="Workout Graph"
          subtitle="Max weight per session for each exercise you log"
        />
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="w-full rounded-xl border border-border bg-muted/50 px-3 py-2 text-sm transition-all focus:outline-none focus:ring-2 focus:ring-primary/40 sm:w-auto"
        >
          {PERIOD_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="luxury-spinner" />
        </div>
      ) : (
        <ScrollReveal animation="blur-up">
          <ExerciseProgressCharts
            strengthProgression={charts?.strength_progression ?? []}
            chartHeight={280}
            emptyMessage="No workout data yet. Log a workout to see your progress graphs."
          />
        </ScrollReveal>
      )}
    </div>
  )
}
