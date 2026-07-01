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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDate } from '@/lib/utils'

const CHART_GOLD = '#c9a962'
const CHART_CHAMPAGNE = '#e8d5b5'
const CHART_GRID = 'rgba(201, 169, 98, 0.08)'
const CHART_AXIS = '#8a8278'
const TOOLTIP_STYLE = {
  background: 'rgba(16, 14, 12, 0.95)',
  border: '1px solid rgba(201, 169, 98, 0.2)',
  borderRadius: 12,
  boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
}

export function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [charts, setCharts] = useState<DashboardCharts | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([api.getDashboard(), api.getCharts(30)])
      .then(([s, c]) => { setStats(s); setCharts(c) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="luxury-spinner" />
      </div>
    )
  }

  const statItems = [
    { title: 'Weight', value: stats?.current_weight ? `${stats.current_weight} kg` : '—', icon: <Scale className="h-5 w-5" /> },
    { title: 'Body Fat', value: stats?.current_body_fat ? `${stats.current_body_fat}%` : '—', icon: <Percent className="h-5 w-5" /> },
    { title: 'Goal Progress', value: `${stats?.goal_progress_percent ?? 0}%`, subtitle: stats?.active_goal?.title, icon: <FlameKindling className="h-5 w-5" /> },
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

      <div className="animate-fade-up stagger-2">
        <GoalSection stats={stats} />
      </div>

      <div className="grid gap-4 grid-cols-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {statItems.map((item, i) => (
          <StatCard key={item.title} {...item} index={i} />
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Weight Trend" delay={3}>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={charts?.weight_trend ?? []}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
              <XAxis dataKey="date" tickFormatter={(d) => formatDate(d)} stroke={CHART_AXIS} fontSize={11} />
              <YAxis stroke={CHART_AXIS} fontSize={11} domain={['auto', 'auto']} />
              <Tooltip contentStyle={TOOLTIP_STYLE} labelFormatter={(d) => formatDate(d)} />
              <Line type="monotone" dataKey="value" stroke={CHART_GOLD} strokeWidth={2.5} dot={false} activeDot={{ r: 4, fill: CHART_GOLD, stroke: CHART_CHAMPAGNE }} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Body Fat Trend" delay={4}>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={charts?.body_fat_trend ?? []}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
              <XAxis dataKey="date" tickFormatter={(d) => formatDate(d)} stroke={CHART_AXIS} fontSize={11} />
              <YAxis stroke={CHART_AXIS} fontSize={11} domain={['auto', 'auto']} />
              <Tooltip contentStyle={TOOLTIP_STYLE} labelFormatter={(d) => formatDate(d)} />
              <Line type="monotone" dataKey="value" stroke={CHART_CHAMPAGNE} strokeWidth={2.5} dot={false} activeDot={{ r: 4, fill: CHART_CHAMPAGNE, stroke: CHART_GOLD }} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Protein Intake" delay={5}>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={charts?.protein_intake ?? []}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
              <XAxis dataKey="date" tickFormatter={(d) => formatDate(d)} stroke={CHART_AXIS} fontSize={11} />
              <YAxis stroke={CHART_AXIS} fontSize={11} unit="g" />
              <Tooltip contentStyle={TOOLTIP_STYLE} labelFormatter={(d) => formatDate(d)} />
              <Bar dataKey="value" fill={CHART_GOLD} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Calorie Intake" delay={6}>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={charts?.calories_intake ?? []}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
              <XAxis dataKey="date" tickFormatter={(d) => formatDate(d)} stroke={CHART_AXIS} fontSize={11} />
              <YAxis stroke={CHART_AXIS} fontSize={11} />
              <Tooltip contentStyle={TOOLTIP_STYLE} labelFormatter={(d) => formatDate(d)} />
              <Bar dataKey="value" fill={CHART_CHAMPAGNE} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="space-y-4 animate-fade-up stagger-7">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-lg font-semibold font-display gradient-text-subtle">Exercise Progress</h2>
          <Link
            to="/workout-graph"
            className="text-sm text-primary hover:text-accent transition-colors font-medium"
          >
            Open workout graph →
          </Link>
        </div>
        <ExerciseProgressCharts
          strengthProgression={charts?.strength_progression ?? []}
          chartHeight={180}
        />
      </div>
    </div>
  )
}

function ChartCard({
  title,
  children,
  className = '',
  delay = 0,
}: {
  title: string
  children: React.ReactNode
  className?: string
  delay?: number
}) {
  return (
    <Card className={`animate-fade-up stagger-${Math.min(delay, 8)} ${className}`}>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}
