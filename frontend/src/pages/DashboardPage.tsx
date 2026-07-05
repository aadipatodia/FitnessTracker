import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar,
} from 'recharts'
import { Scale, Percent, Flame, Beef, Heart, FlameKindling, Dumbbell } from 'lucide-react'
import { api, DashboardStats, DashboardCharts } from '@/lib/api'
import { StatCard } from '@/components/StatCard'
import { GoalSection } from '@/components/GoalSection'
import { ExerciseProgressCharts } from '@/components/ExerciseProgressCharts'
import { PageHeader } from '@/components/PageHeader'
import { ScrollReveal, revealDelay } from '@/components/ScrollReveal'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDate } from '@/lib/utils'

const CHART_GOLD = '#c9a962'
const CHART_CHAMPAGNE = '#e8d5b5'
const CHART_GRID = 'rgba(201, 169, 98, 0.08)'
const CHART_AXIS = '#c4b89a'
const TOOLTIP_STYLE = {
  background: 'rgba(16, 14, 12, 0.95)',
  border: '1px solid rgba(201, 169, 98, 0.2)',
  borderRadius: 12,
  boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
}

export function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [charts, setCharts] = useState<DashboardCharts | null>(null)
  const [statsLoading, setStatsLoading] = useState(true)
  const [chartsLoading, setChartsLoading] = useState(true)

  useEffect(() => {
    api.getDashboard()
      .then(setStats)
      .catch(console.error)
      .finally(() => setStatsLoading(false))

    api.getCharts(30)
      .then(setCharts)
      .catch(console.error)
      .finally(() => setChartsLoading(false))
  }, [])

  if (statsLoading && !stats) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="luxury-spinner" />
      </div>
    )
  }

  const statItems = [
    { title: 'Weight', value: stats?.current_weight ? `${stats.current_weight} kg` : '—', icon: <Scale className="h-5 w-5" /> },
    { title: 'Body Fat', value: stats?.current_body_fat ? `${stats.current_body_fat}%` : '—', icon: <Percent className="h-5 w-5" /> },
    { title: 'Goal Progress', value: `${stats?.goal_progress_percent ?? 0}%`, subtitle: stats?.deadline_status && stats.deadline_status !== 'no_deadline' ? stats.deadline_status.replace('_', ' ') : 'routine + diet + workouts', icon: <FlameKindling className="h-5 w-5" /> },
    { title: 'Calories Today', value: Math.round(stats?.calories_today ?? 0), subtitle: stats?.target_calories ? `/ ${stats.target_calories} target` : undefined, icon: <Flame className="h-5 w-5" /> },
    {
      title: 'Calories Burned',
      value: Math.round(stats?.calories_burned_today ?? 0),
      subtitle:
        (stats?.calories_burned_today ?? 0) > 0
          ? [
              stats?.calories_burned_everyday ? `${Math.round(stats.calories_burned_everyday)} everyday` : null,
              stats?.calories_burned_workouts ? `${Math.round(stats.calories_burned_workouts)} gym` : null,
              stats?.calories_burned_cardio ? `${Math.round(stats.calories_burned_cardio)} cardio` : null,
            ].filter(Boolean).join(' · ') || `net ${Math.round((stats?.calories_today ?? 0) - (stats?.calories_burned_today ?? 0))} kcal`
          : 'everyday movement + logged exercise',
      icon: <Dumbbell className="h-5 w-5" />,
    },
    { title: 'Protein Today', value: `${Math.round(stats?.protein_today ?? 0)}g`, subtitle: stats?.target_protein ? `/ ${stats.target_protein}g target` : undefined, icon: <Beef className="h-5 w-5" /> },
    { title: 'Recovery Score', value: `${stats?.recovery_score ?? 0}%`, subtitle: `${stats?.workout_streak ?? 0} day streak`, icon: <Heart className="h-5 w-5" /> },
  ]

  return (
    <div className="space-y-7">
      <PageHeader
        title="Dashboard"
        subtitle={stats?.active_goal?.title || 'Track your fitness journey'}
      />

      <ScrollReveal animation="fade-up" duration={800}>
        <GoalSection stats={stats} />
      </ScrollReveal>

      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3">
        {statItems.map((item, i) => (
          <ScrollReveal key={item.title} delay={revealDelay(i, 70)} animation="scale">
            <StatCard {...item} />
          </ScrollReveal>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {chartsLoading ? (
          <>
            <ChartSkeleton title="Weight Trend" />
            <ChartSkeleton title="Body Fat Trend" />
            <ChartSkeleton title="Protein Intake" />
            <ChartSkeleton title="Calorie Intake" />
          </>
        ) : (
          <>
        <ChartCard title="Weight Trend" index={0}>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={charts?.weight_trend ?? []}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
              <XAxis dataKey="date" tickFormatter={(d) => formatDate(d)} stroke={CHART_AXIS} fontSize={13} tick={{ fill: CHART_AXIS }} />
              <YAxis stroke={CHART_AXIS} fontSize={13} tick={{ fill: CHART_AXIS }} domain={['auto', 'auto']} />
              <Tooltip contentStyle={TOOLTIP_STYLE} labelFormatter={(d) => formatDate(d)} />
              <Line type="monotone" dataKey="value" stroke={CHART_GOLD} strokeWidth={2.5} dot={false} activeDot={{ r: 4, fill: CHART_GOLD, stroke: CHART_CHAMPAGNE }} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Body Fat Trend" index={1}>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={charts?.body_fat_trend ?? []}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
              <XAxis dataKey="date" tickFormatter={(d) => formatDate(d)} stroke={CHART_AXIS} fontSize={13} tick={{ fill: CHART_AXIS }} />
              <YAxis stroke={CHART_AXIS} fontSize={13} tick={{ fill: CHART_AXIS }} domain={['auto', 'auto']} />
              <Tooltip contentStyle={TOOLTIP_STYLE} labelFormatter={(d) => formatDate(d)} />
              <Line type="monotone" dataKey="value" stroke={CHART_CHAMPAGNE} strokeWidth={2.5} dot={false} activeDot={{ r: 4, fill: CHART_CHAMPAGNE, stroke: CHART_GOLD }} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Protein Intake" index={2} animation="slide-left">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={charts?.protein_intake ?? []}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
              <XAxis dataKey="date" tickFormatter={(d) => formatDate(d)} stroke={CHART_AXIS} fontSize={13} tick={{ fill: CHART_AXIS }} />
              <YAxis stroke={CHART_AXIS} fontSize={13} tick={{ fill: CHART_AXIS }} unit="g" />
              <Tooltip contentStyle={TOOLTIP_STYLE} labelFormatter={(d) => formatDate(d)} />
              <Bar dataKey="value" fill={CHART_GOLD} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Calorie Intake" index={3} animation="slide-right">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={charts?.calories_intake ?? []}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
              <XAxis dataKey="date" tickFormatter={(d) => formatDate(d)} stroke={CHART_AXIS} fontSize={13} tick={{ fill: CHART_AXIS }} />
              <YAxis stroke={CHART_AXIS} fontSize={13} tick={{ fill: CHART_AXIS }} />
              <Tooltip contentStyle={TOOLTIP_STYLE} labelFormatter={(d) => formatDate(d)} />
              <Bar dataKey="value" fill={CHART_CHAMPAGNE} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
          </>
        )}
      </div>

      <ScrollReveal animation="fade-up" delay={100}>
        <div className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="text-xl font-semibold font-display text-foreground">Exercise Progress</h2>
            <Link
              to="/workout-graph"
              className="text-base text-primary hover:text-accent transition-colors font-semibold"
            >
              Open workout graph →
            </Link>
          </div>
          {chartsLoading ? (
            <Card>
              <CardContent className="flex items-center justify-center gap-3 py-16">
                <div className="luxury-spinner" />
                <p className="text-sm text-muted-foreground">Loading exercise charts…</p>
              </CardContent>
            </Card>
          ) : (
          <ExerciseProgressCharts
            strengthProgression={charts?.strength_progression ?? []}
            exerciseAssessments={charts?.exercise_assessments ?? []}
            chartHeight={180}
          />
          )}
        </div>
      </ScrollReveal>
    </div>
  )
}

function ChartSkeleton({ title }: { title: string }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="flex items-center justify-center h-[220px]">
        <div className="luxury-spinner" />
      </CardContent>
    </Card>
  )
}

function ChartCard({
  title,
  children,
  className = '',
  index = 0,
  animation = 'fade-up',
}: {
  title: string
  children: React.ReactNode
  className?: string
  index?: number
  animation?: 'fade-up' | 'slide-left' | 'slide-right'
}) {
  return (
    <ScrollReveal animation={animation} delay={revealDelay(index, 100)} className={className}>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>{children}</CardContent>
      </Card>
    </ScrollReveal>
  )
}
