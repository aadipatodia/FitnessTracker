import { useCallback, useEffect, useState } from 'react'
import { Brain, Sparkles, Calendar, TrendingUp, Target } from 'lucide-react'
import { api, CoachingInsight } from '@/lib/api'
import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDate, todayISO } from '@/lib/utils'

type AnalysisType = 'daily' | 'weekly' | 'goal'

const insightIcons: Record<string, React.ReactNode> = {
  daily: <Brain className="h-4 w-4" />,
  weekly: <Calendar className="h-4 w-4" />,
  progression: <TrendingUp className="h-4 w-4" />,
  nutrition: <Sparkles className="h-4 w-4" />,
  goal_estimate: <Target className="h-4 w-4" />,
}

const insightColors: Record<string, string> = {
  daily: 'text-primary bg-primary/10',
  weekly: 'text-accent bg-accent/10',
  progression: 'text-amber-400 bg-amber-400/10',
  nutrition: 'text-emerald-400 bg-emerald-400/10',
  goal_estimate: 'text-violet-400 bg-violet-400/10',
}

const sectionConfig: { type: AnalysisType; title: string; description: string }[] = [
  {
    type: 'daily',
    title: 'Daily Analysis',
    description: 'Workouts, diet, and recovery for the selected date only.',
  },
  {
    type: 'weekly',
    title: 'Weekly Summary',
    description: 'Compact 7-day trends ending on the selected date.',
  },
  {
    type: 'goal',
    title: 'Goal Progress',
    description: 'Overall progress since your goal was set and advice to hit your deadline.',
  },
]

function insightDateLabel(insight: CoachingInsight): string {
  const analysisDate = insight.metadata_json?.analysis_date
  if (analysisDate && typeof analysisDate === 'string') {
    return formatDate(analysisDate)
  }
  return formatDate(insight.created_at)
}

function CalorieBalanceSummary({ metadata }: { metadata: CoachingInsight['metadata_json'] }) {
  const balance = metadata?.calorie_balance as {
    calories_consumed?: number
    calories_burned_active_total?: number
    calories_burned_everyday_movement?: number
    calories_burned_exercise?: number
    calories_burned_workouts?: number
    calories_burned_cardio?: number
    target_calories?: number
    target_calorie_burn?: number
    target_calorie_burn_mode?: 'surplus_offset' | 'workout_minimum'
    minimum_workout_calorie_burn?: number
    calories_remaining_to_eat?: number
    calories_over_target?: number
    intake_surplus_after_exercise?: number
  } | undefined

  if (!balance?.target_calories) return null

  const everyday = balance.calories_burned_everyday_movement ?? 0
  const workoutBurn = balance.calories_burned_workouts ?? 0
  const cardioBurn = balance.calories_burned_cardio ?? 0
  const burnTarget = balance.target_calorie_burn
  const burnTargetMode = balance.target_calorie_burn_mode
  const minWorkoutBurn = balance.minimum_workout_calorie_burn
  const overTarget = balance.calories_over_target ?? 0

  return (
    <div className="mt-3 space-y-2">
      <div className="grid gap-2 grid-cols-2 sm:grid-cols-2 lg:grid-cols-5">
        <div className="rounded-lg bg-muted/50 px-3 py-2 text-sm">
          <p className="text-xs text-muted-foreground">Eaten</p>
          <p className="font-medium">{Math.round(balance.calories_consumed ?? 0)} kcal</p>
        </div>
        <div className="rounded-lg bg-muted/50 px-3 py-2 text-sm">
          <p className="text-xs text-muted-foreground">Workout burn</p>
          <p className="font-medium">{Math.round(workoutBurn)} kcal</p>
        </div>
        <div className="rounded-lg bg-muted/50 px-3 py-2 text-sm">
          <p className="text-xs text-muted-foreground">Intake target</p>
          <p className="font-medium">{balance.target_calories} kcal</p>
        </div>
        {burnTarget != null && (
          <div className="rounded-lg bg-muted/50 px-3 py-2 text-sm">
            <p className="text-xs text-muted-foreground">Burn target</p>
            <p className="font-medium">{Math.round(burnTarget)} kcal</p>
            <p className="text-[10px] text-muted-foreground">
              {burnTargetMode === 'surplus_offset'
                ? burnTarget > 0
                  ? 'extra to burn'
                  : 'surplus covered'
                : 'per workout'}
            </p>
          </div>
        )}
        <div className="rounded-lg bg-primary/10 px-3 py-2 text-sm">
          <p className="text-xs text-muted-foreground">
            {(balance.calories_over_target ?? 0) > 0 ? 'Over target' : 'Remaining'}
          </p>
          <p className="font-medium text-primary">
            {(balance.calories_over_target ?? 0) > 0
              ? `${Math.round(balance.calories_over_target ?? 0)} kcal`
              : `${Math.round(balance.calories_remaining_to_eat ?? 0)} kcal`}
          </p>
        </div>
      </div>
      <p className="text-xs text-muted-foreground">
        ~{Math.round(everyday)} kcal everyday movement (auto, from body weight)
        {burnTargetMode === 'surplus_offset' && overTarget > 0 && (
          <>
            {' '}
            · {Math.round(overTarget)} kcal over intake,{' '}
            {Math.round(workoutBurn + cardioBurn)} kcal already burned from exercise
            {burnTarget != null && burnTarget > 0 && (
              <> · burn {Math.round(burnTarget)} kcal more to offset the rest</>
            )}
            {burnTarget === 0 && <> · exercise covered today&apos;s surplus</>}
          </>
        )}
        {burnTargetMode === 'workout_minimum' && minWorkoutBurn != null && (
          <> · Aim for at least {Math.round(minWorkoutBurn)} kcal per workout</>
        )}
      </p>
    </div>
  )
}

function InsightCard({ insight }: { insight: CoachingInsight }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center gap-3">
          <div
            className={`flex h-8 w-8 items-center justify-center rounded-lg ${
              insightColors[insight.insight_type] || 'bg-muted text-muted-foreground'
            }`}
          >
            {insightIcons[insight.insight_type] || <Brain className="h-4 w-4" />}
          </div>
          <div className="flex-1">
            <CardTitle className="text-base">{insight.title}</CardTitle>
            <p className="text-xs text-muted-foreground capitalize">
              {insight.insight_type.replace('_', ' ')}
              {' · '}
              {insight.metadata_json?.analysis_type === 'weekly'
                ? `Week ending ${insightDateLabel(insight)}`
                : insightDateLabel(insight)}
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm leading-relaxed">{insight.content}</p>
        {insight.metadata_json?.analysis_type === 'daily' && (
          <CalorieBalanceSummary metadata={insight.metadata_json} />
        )}
        {insight.metadata_json?.calorie_recommendation != null && (
          <div className="mt-3 rounded-lg bg-emerald-400/10 px-3 py-2 text-sm text-emerald-300">
            Calorie target: {String(insight.metadata_json.calorie_recommendation)} kcal/day
            {insight.metadata_json.protein_recommendation != null && (
              <> · Protein target: {String(insight.metadata_json.protein_recommendation)}g</>
            )}
          </div>
        )}
        {insight.metadata_json?.goal_completion_weeks != null && (
          <div className="mt-3 rounded-lg bg-violet-400/10 px-3 py-2 text-sm text-violet-300">
            Estimated goal completion: {String(insight.metadata_json.goal_completion_weeks)} weeks
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export function CoachPage() {
  const [insightsByType, setInsightsByType] = useState<Record<AnalysisType, CoachingInsight[]>>({
    daily: [],
    weekly: [],
    goal: [],
  })
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState<AnalysisType | null>(null)
  const [analysisDate, setAnalysisDate] = useState(todayISO())

  const loadInsights = useCallback(async (date: string) => {
    setLoading(true)
    try {
      const [daily, weekly, goal] = await Promise.all([
        api.getInsights({ analysisDate: date, analysisType: 'daily' }),
        api.getInsights({ analysisDate: date, analysisType: 'weekly' }),
        api.getInsights({ analysisDate: date, analysisType: 'goal' }),
      ])
      setInsightsByType({ daily, weekly, goal })
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadInsights(analysisDate)
  }, [analysisDate, loadInsights])

  const runAnalysis = async (type: AnalysisType) => {
    setAnalyzing(type)
    try {
      const newInsights = await api.analyze(type, analysisDate)
      setInsightsByType((prev) => ({ ...prev, [type]: newInsights }))
    } catch (err) {
      console.error(err)
    } finally {
      setAnalyzing(null)
    }
  }

  const hasAnyInsights = Object.values(insightsByType).some((list) => list.length > 0)

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4">
        <PageHeader title="AI Coach" subtitle="Personalized feedback powered by Gemini" />

        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
          <div className="space-y-1.5">
            <label htmlFor="analysis-date" className="text-xs font-medium text-muted-foreground">
              Analyze date
            </label>
            <Input
              id="analysis-date"
              type="date"
              max={todayISO()}
              value={analysisDate}
              onChange={(e) => setAnalysisDate(e.target.value)}
              className="w-full sm:w-44"
            />
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
            <Button
              variant="outline"
              onClick={() => runAnalysis('daily')}
              disabled={analyzing !== null || !analysisDate}
              className="w-full sm:w-auto"
            >
              {analyzing === 'daily' ? 'Analyzing...' : 'Analyze Day'}
            </Button>
            <Button
              variant="outline"
              onClick={() => runAnalysis('weekly')}
              disabled={analyzing !== null}
              className="w-full sm:w-auto"
            >
              {analyzing === 'weekly' ? 'Analyzing...' : 'Weekly Summary'}
            </Button>
            <Button onClick={() => runAnalysis('goal')} disabled={analyzing !== null} className="w-full sm:w-auto">
              {analyzing === 'goal' ? 'Analyzing...' : 'Goal Progress'}
            </Button>
          </div>
        </div>
      </div>

      <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-accent/5">
        <CardContent className="py-6">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/20">
              <Brain className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h3 className="font-semibold">How it works</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Analyze Day covers only the selected date. Weekly Summary uses a compact 7-day rollup
                (less data sent to AI). Goal Progress reviews everything since your goal was set and
                advises on hitting your deadline.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="luxury-spinner" />
        </div>
      ) : !hasAnyInsights ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Brain className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              No insights for {formatDate(analysisDate)} yet. Run an analysis above.
            </p>
            <Button
              className="mt-4"
              onClick={() => runAnalysis('daily')}
              disabled={analyzing !== null}
            >
              Analyze {formatDate(analysisDate)}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-8">
          {sectionConfig.map(({ type, title, description }) => {
            const insights = insightsByType[type]
            if (insights.length === 0) return null
            return (
              <section key={type} className="space-y-3">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h2 className="text-lg font-semibold">{title}</h2>
                    <p className="text-sm text-muted-foreground">{description}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => runAnalysis(type)}
                    disabled={analyzing !== null}
                  >
                    {analyzing === type ? 'Refreshing...' : 'Refresh'}
                  </Button>
                </div>
                <div className="space-y-4">
                  {insights.map((insight) => (
                    <InsightCard key={insight.id} insight={insight} />
                  ))}
                </div>
              </section>
            )
          })}
        </div>
      )}
    </div>
  )
}
