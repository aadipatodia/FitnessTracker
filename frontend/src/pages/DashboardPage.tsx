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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDate } from '@/lib/utils'

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
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    )
  }
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">
          {stats?.active_goal?.title || 'Track your fitness journey'}
        </p>
      </div>

      <GoalSection stats={stats} />

      {/* Stats grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <StatCard
          title="Weight"
          value={stats?.current_weight ? `${stats.current_weight} kg` : '—'}
          icon={<Scale className="h-5 w-5" />}
        />
        <StatCard
          title="Body Fat"
          value={stats?.current_body_fat ? `${stats.current_body_fat}%` : '—'}
          icon={<Percent className="h-5 w-5" />}
        />
        <StatCard
          title="Goal Progress"
          value={`${stats?.goal_progress_percent ?? 0}%`}
          subtitle={stats?.active_goal?.title}
          icon={<FlameKindling className="h-5 w-5" />}
        />
        <StatCard
          title="Calories Today"
          value={Math.round(stats?.calories_today ?? 0)}
          subtitle={stats?.target_calories ? `/ ${stats.target_calories} target` : undefined}
          icon={<Flame className="h-5 w-5" />}
        />
        <StatCard
          title="Calories Burned"
          value={Math.round(stats?.calories_burned_today ?? 0)}
          subtitle={
            (stats?.calories_burned_today ?? 0) > 0
              ? [
                  stats?.calories_burned_everyday ? `${Math.round(stats.calories_burned_everyday)} everyday` : null,
                  stats?.calories_burned_workouts ? `${Math.round(stats.calories_burned_workouts)} gym` : null,
                  stats?.calories_burned_cardio ? `${Math.round(stats.calories_burned_cardio)} cardio` : null,
                ].filter(Boolean).join(' · ') || `net ${Math.round((stats?.calories_today ?? 0) - (stats?.calories_burned_today ?? 0))} kcal`
              : 'everyday movement + logged exercise'
          }
          icon={<Dumbbell className="h-5 w-5" />}
        />
        <StatCard
          title="Protein Today"
          value={`${Math.round(stats?.protein_today ?? 0)}g`}
          subtitle={stats?.target_protein ? `/ ${stats.target_protein}g target` : undefined}
          icon={<Beef className="h-5 w-5" />}
        />
        <StatCard
          title="Recovery Score"
          value={`${stats?.recovery_score ?? 0}%`}
          subtitle={`${stats?.workout_streak ?? 0} day streak`}
          icon={<Heart className="h-5 w-5" />}
        />
      </div>

      {/* Charts */}
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Weight Trend">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={charts?.weight_trend ?? []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
              <XAxis dataKey="date" tickFormatter={(d) => formatDate(d)} stroke="#71717a" fontSize={11} />
              <YAxis stroke="#71717a" fontSize={11} domain={['auto', 'auto']} />
              <Tooltip
                contentStyle={{ background: '#12121a', border: '1px solid #27272a', borderRadius: 8 }}
                labelFormatter={(d) => formatDate(d)}
              />
              <Line type="monotone" dataKey="value" stroke="#22c55e" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Body Fat Trend">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={charts?.body_fat_trend ?? []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
              <XAxis dataKey="date" tickFormatter={(d) => formatDate(d)} stroke="#71717a" fontSize={11} />
              <YAxis stroke="#71717a" fontSize={11} domain={['auto', 'auto']} />
              <Tooltip
                contentStyle={{ background: '#12121a', border: '1px solid #27272a', borderRadius: 8 }}
                labelFormatter={(d) => formatDate(d)}
              />
              <Line type="monotone" dataKey="value" stroke="#6366f1" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Protein Intake">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={charts?.protein_intake ?? []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
              <XAxis dataKey="date" tickFormatter={(d) => formatDate(d)} stroke="#71717a" fontSize={11} />
              <YAxis stroke="#71717a" fontSize={11} unit="g" />
              <Tooltip
                contentStyle={{ background: '#12121a', border: '1px solid #27272a', borderRadius: 8 }}
                labelFormatter={(d) => formatDate(d)}
              />
              <Bar dataKey="value" fill="#22c55e" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Calorie Intake">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={charts?.calories_intake ?? []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
              <XAxis dataKey="date" tickFormatter={(d) => formatDate(d)} stroke="#71717a" fontSize={11} />
              <YAxis stroke="#71717a" fontSize={11} />
              <Tooltip
                contentStyle={{ background: '#12121a', border: '1px solid #27272a', borderRadius: 8 }}
                labelFormatter={(d) => formatDate(d)}
              />
              <Bar dataKey="value" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-lg font-semibold">Exercise Progress</h2>
          <Link
            to="/workout-graph"
            className="text-sm text-primary hover:underline"
          >
            Open workout graph
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

function ChartCard({ title, children, className = '' }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}
