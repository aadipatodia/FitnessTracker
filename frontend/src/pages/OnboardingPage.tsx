import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Target, Flame, Dumbbell, TrendingDown, Lightbulb } from 'lucide-react'
import { api, type GoalFeasibility, type GoalGuidance } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/ui/button'
import { Input, Label, Textarea, Select } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { GoalPlanAssessment } from '@/components/GoalPlanAssessment'

type GoalType = 'reduce_body_fat' | 'lose_fat_gain_muscle' | 'increase_strength' | 'general_fitness'
type Gender = 'male' | 'female'

const genderOptions: { value: Gender; label: string }[] = [
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
]

const goalTypes = [
  { value: 'reduce_body_fat' as GoalType, label: 'Reduce Body Fat', icon: TrendingDown, desc: 'Cut fat to a target percentage' },
  { value: 'lose_fat_gain_muscle' as GoalType, label: 'Recomposition', icon: Flame, desc: 'Lose fat while building muscle' },
  { value: 'increase_strength' as GoalType, label: 'Increase Strength', icon: Dumbbell, desc: 'Get stronger in key lifts' },
  { value: 'general_fitness' as GoalType, label: 'General Fitness', icon: Target, desc: 'Overall health and fitness' },
]

function parseDateFromText(text: string): string | null {
  const iso = text.match(/\b(\d{4}-\d{2}-\d{2})\b/)
  if (iso) return iso[1]

  const dmy = text.match(/\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b/)
  if (dmy) {
    const [, d, m, y] = dmy
    return `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`
  }

  const monthNames =
    'january|february|march|april|may|june|july|august|september|october|november|december'
  const named =
    text.match(new RegExp(`\\b(\\d{1,2})\\s+(?:${monthNames})\\s+(\\d{4})\\b`, 'i')) ??
    text.match(new RegExp(`\\b(?:${monthNames})\\s+(\\d{1,2}),?\\s+(\\d{4})\\b`, 'i'))
  if (named) {
    const parsed = new Date(named[0])
    if (!Number.isNaN(parsed.getTime())) return parsed.toISOString().slice(0, 10)
  }

  return null
}

function parseNutritionFromText(text: string): { calories?: number; protein?: number } {
  const lowered = text.toLowerCase()
  const result: { calories?: number; protein?: number } = {}

  const calorieRange =
    lowered.match(/(?:consume|eat|intake|have to consume)?\s*(\d{3,4})\s*(?:-|–|to)\s*(\d{3,4})\s*(?:cal(?:ories)?|kcal)\b/) ??
    lowered.match(/(\d{3,4})\s*(?:-|–|to)\s*(\d{3,4})\s*(?:cal(?:ories)?|kcal)\b/)
  if (calorieRange) {
    const low = Number(calorieRange[1])
    const high = Number(calorieRange[2])
    if (low >= 800 && high <= 6000 && low <= high) {
      result.calories = Math.round((low + high) / 2)
    }
  } else {
    const singleCalorie = lowered.match(/\b(\d{3,4})\s*(?:cal(?:ories)?|kcal)\b/)
    if (singleCalorie) {
      const value = Number(singleCalorie[1])
      if (value >= 800 && value <= 6000) result.calories = value
    }
  }

  const proteinRange = lowered.match(/(\d{2,3})\s*(?:-|–|to)\s*(\d{2,3})\s*g?\s*protein/)
  if (proteinRange) {
    const low = Number(proteinRange[1])
    const high = Number(proteinRange[2])
    if (low >= 50 && high <= 400 && low <= high) {
      result.protein = Math.round((low + high) / 2)
    }
  } else {
    const singleProtein = lowered.match(/\b(\d{2,3})\s*g\s+protein/)
    if (singleProtein) {
      const value = Number(singleProtein[1])
      if (value >= 50 && value <= 400) result.protein = value
    }
  }

  return result
}

function weeksUntil(dateStr: string): number {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const deadline = new Date(dateStr + 'T00:00:00')
  const days = Math.max(0, Math.ceil((deadline.getTime() - today.getTime()) / (1000 * 60 * 60 * 24)))
  if (days === 0) return 0
  return Math.max(1, Math.ceil(days / 7))
}

function buildPlanInputKey(fields: Record<string, string>) {
  return JSON.stringify(fields)
}

export function OnboardingPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [step, setStep] = useState(0)
  const [selectedGoalTypes, setSelectedGoalTypes] = useState<GoalType[]>(['reduce_body_fat'])

  const toggleGoalType = (value: GoalType) => {
    setSelectedGoalTypes((prev) =>
      prev.includes(value) ? prev.filter((t) => t !== value) : [...prev, value]
    )
  }

  const goalTypeForApi = selectedGoalTypes.join(',')
  const primaryGoalType = selectedGoalTypes[0] ?? 'reduce_body_fat'
  const selectedGoalLabels = selectedGoalTypes
    .map((t) => goalTypes.find((g) => g.value === t)?.label)
    .filter(Boolean)
    .join(' & ')
  const [gender, setGender] = useState<Gender | ''>('')
  const [age, setAge] = useState('')
  const [endGoal, setEndGoal] = useState('')
  const [title, setTitle] = useState('')
  const [currentWeight, setCurrentWeight] = useState('')
  const [targetWeight, setTargetWeight] = useState('')
  const [currentBodyFat, setCurrentBodyFat] = useState('')
  const [targetBodyFat, setTargetBodyFat] = useState('')
  const [targetExercise, setTargetExercise] = useState('')
  const [currentLift, setCurrentLift] = useState('')
  const [targetLift, setTargetLift] = useState('')
  const [targetDate, setTargetDate] = useState('')
  const [targetCalories, setTargetCalories] = useState('')
  const [targetProtein, setTargetProtein] = useState('')
  const [guidance, setGuidance] = useState<GoalGuidance | null>(null)
  const [guidanceLoading, setGuidanceLoading] = useState(false)
  const [feasibility, setFeasibility] = useState<GoalFeasibility | null>(null)
  const [planLoading, setPlanLoading] = useState(false)
  const [acknowledgedExtreme, setAcknowledgedExtreme] = useState(false)
  const [loading, setLoading] = useState(false)
  const [planAnalyzed, setPlanAnalyzed] = useState(false)
  const lastAnalyzedInput = useRef('')

  useEffect(() => {
    if (user?.gender && !gender) setGender(user.gender as Gender)
    if (user?.age && !age) setAge(String(user.age))
  }, [user, gender, age])

  const parsedAge = age !== '' && !Number.isNaN(Number(age)) ? parseInt(age, 10) : undefined
  const profileComplete = Boolean(
    gender && parsedAge !== undefined && parsedAge >= 0 && parsedAge <= 100
  )

  const parsedGoalDate = parseDateFromText(endGoal)
  const planInputKey = buildPlanInputKey({
    goalType: goalTypeForApi,
    gender,
    age,
    endGoal,
    targetDate: targetDate || parsedGoalDate || '',
    currentWeight,
    targetWeight,
    currentBodyFat,
    targetBodyFat,
    targetExercise,
    currentLift,
    targetLift,
  })

  const guidanceFetchedForStep = useRef('')

  useEffect(() => {
    if (step !== 2 || !endGoal.trim() || !gender || parsedAge === undefined) return

    const guidanceKey = `${goalTypeForApi}|${endGoal}|${gender}|${parsedAge}`
    if (guidanceFetchedForStep.current === guidanceKey) return
    guidanceFetchedForStep.current = guidanceKey

    let cancelled = false
    setGuidanceLoading(true)
    api
      .getGoalGuidance({
        goal_type: goalTypeForApi,
        end_goal: endGoal.trim() || undefined,
        gender,
        age: parsedAge,
      })
      .then((g) => {
        if (!cancelled) setGuidance(g)
      })
      .catch(console.error)
      .finally(() => {
        if (!cancelled) setGuidanceLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [step, goalTypeForApi, endGoal, gender, parsedAge])

  useEffect(() => {
    if (step !== 2) {
      setPlanAnalyzed(false)
      lastAnalyzedInput.current = ''
      return
    }
    if (planAnalyzed && planInputKey !== lastAnalyzedInput.current) {
      setPlanAnalyzed(false)
      setFeasibility(null)
      setAcknowledgedExtreme(false)
    }
  }, [step, planInputKey, planAnalyzed])

  const effectiveTargetDate =
    targetDate || parsedGoalDate || feasibility?.recommended_target_date || undefined
  const weeksUntilDeadline = effectiveTargetDate
    ? weeksUntil(effectiveTargetDate)
    : (feasibility?.recommended_weeks ?? 0)

  const hasAssessment = feasibility != null && (
    feasibility.headline.length > 0 ||
    feasibility.expected_by_deadline.length > 0 ||
    feasibility.aggressive_plan.length > 0
  )
  const needsExtremeAck =
    hasAssessment && (feasibility!.intensity === 'extreme' || !feasibility!.realistic)

  const analyzePlan = async (): Promise<GoalFeasibility | null> => {
    if (!profileComplete) return null
    setPlanLoading(true)
    try {
      const effectiveDate = effectiveTargetDate

      const result = await api.evaluateGoal({
        goal_type: goalTypeForApi,
        end_goal: endGoal.trim() || undefined,
        gender,
        age: parsedAge,
        target_date: effectiveDate,
        current_weight: currentWeight ? parseFloat(currentWeight) : undefined,
        target_weight: targetWeight ? parseFloat(targetWeight) : undefined,
        current_body_fat: currentBodyFat ? parseFloat(currentBodyFat) : undefined,
        target_body_fat: targetBodyFat ? parseFloat(targetBodyFat) : undefined,
        target_exercise: targetExercise || undefined,
        current_weight_lifted: currentLift ? parseFloat(currentLift) : undefined,
        target_weight_lifted: targetLift ? parseFloat(targetLift) : undefined,
      })

      setFeasibility(result)
      lastAnalyzedInput.current = planInputKey
      setPlanAnalyzed(true)
      setAcknowledgedExtreme(false)
      if (!targetDate && parsedGoalDate) setTargetDate(parsedGoalDate)
      if (!targetDate && !parsedGoalDate && result.recommended_target_date) {
        setTargetDate(result.recommended_target_date)
      }
      if (result.target_calories) setTargetCalories(String(result.target_calories))
      if (result.target_protein) setTargetProtein(String(result.target_protein))
      return result
    } catch (err) {
      console.error(err)
      return null
    } finally {
      setPlanLoading(false)
    }
  }

  const handleSubmit = async () => {
    if (planLoading || loading || !profileComplete) return

    let assessment = feasibility
    if (!planAnalyzed || planInputKey !== lastAnalyzedInput.current) {
      assessment = await analyzePlan()
      if (!assessment) return
      const needsAck =
        (assessment.headline.length > 0 ||
          assessment.expected_by_deadline.length > 0 ||
          assessment.aggressive_plan.length > 0) &&
        (assessment.intensity === 'extreme' || !assessment.realistic)
      if (needsAck) return
    }

    if (needsExtremeAck && !acknowledgedExtreme) return

    setLoading(true)
    try {
      let description = endGoal.trim()
      if (selectedGoalTypes.length > 1) {
        description = `Focus areas: ${selectedGoalLabels}${description ? `\n\n${description}` : ''}`
      }
      const plan = assessment ?? feasibility
      if (plan && (plan.intensity === 'extreme' || !plan.realistic)) {
        description += `\n\n[Plan: ${plan.intensity}] ${plan.expected_by_deadline}`
        if (plan.aggressive_plan) description += ` ${plan.aggressive_plan}`
      }

      await api.createGoal({
        goal_type: primaryGoalType,
        title: title || endGoal.slice(0, 60) || selectedGoalLabels || 'My Goal',
        description: description || undefined,
        gender,
        age: parsedAge,
        current_weight: currentWeight ? parseFloat(currentWeight) : undefined,
        target_weight: targetWeight ? parseFloat(targetWeight) : undefined,
        current_body_fat: currentBodyFat ? parseFloat(currentBodyFat) : undefined,
        target_body_fat: targetBodyFat ? parseFloat(targetBodyFat) : undefined,
        target_exercise: targetExercise || undefined,
        target_weight_lifted: targetLift ? parseFloat(targetLift) : undefined,
        target_calories: targetCalories ? parseInt(targetCalories) : undefined,
        target_protein: targetProtein ? parseInt(targetProtein) : undefined,
        target_date: effectiveTargetDate || assessment?.recommended_target_date,
      })
      navigate('/')
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const showBodyFat = selectedGoalTypes.some(
    (t) => t === 'reduce_body_fat' || t === 'lose_fat_gain_muscle'
  )
  const showWeight = selectedGoalTypes.some((t) => t !== 'increase_strength')
  const showStrength = selectedGoalTypes.includes('increase_strength')

  const minDate = new Date()
  minDate.setDate(minDate.getDate() + 7)
  const minDateStr = minDate.toISOString().slice(0, 10)

  const submitLabel = planLoading
    ? 'Analyzing your plan…'
    : loading
      ? 'Setting up…'
      : planAnalyzed && needsExtremeAck && !acknowledgedExtreme
        ? 'Review plan above, then confirm'
        : planAnalyzed
          ? 'Confirm & start coaching'
          : 'Start coaching'

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-2xl">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold gradient-text">Set Your Goal</h1>
          <p className="mt-2 text-body-secondary">Tell us where you want to end up — we'll guide the path</p>
          <div className="mt-4 flex justify-center gap-2">
            {[0, 1, 2].map((s) => (
              <div
                key={s}
                className={`h-1.5 w-12 rounded-full transition-colors ${step >= s ? 'bg-primary' : 'bg-muted'}`}
              />
            ))}
          </div>
        </div>

        {step === 0 && (
          <Card>
            <CardHeader>
              <CardTitle>What's your focus?</CardTitle>
              <CardDescription>Pick one or more categories that match your end goal</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2">
              {goalTypes.map(({ value, label, icon: Icon, desc }) => {
                const selected = selectedGoalTypes.includes(value)
                return (
                  <button
                    key={value}
                    type="button"
                    onClick={() => toggleGoalType(value)}
                    className={`flex flex-col items-start rounded-xl border p-4 text-left transition-all ${
                      selected
                        ? 'border-primary bg-primary/10'
                        : 'border-border hover:border-primary/50'
                    }`}
                  >
                    <Icon className={`mb-2 h-5 w-5 ${selected ? 'text-primary' : 'text-secondary-foreground'}`} />
                    <span className="font-medium">{label}</span>
                    <span className="text-meta mt-1">{desc}</span>
                  </button>
                )
              })}
              <Button
                className="sm:col-span-2 mt-2"
                onClick={() => setStep(1)}
                disabled={selectedGoalTypes.length === 0}
              >
                Continue
              </Button>
            </CardContent>
          </Card>
        )}

        {step === 1 && (
          <Card>
            <CardHeader>
              <CardTitle>Describe your end goal</CardTitle>
              <CardDescription>What does success look like for you?</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Your end goal</Label>
                <Textarea
                  value={endGoal}
                  onChange={(e) => setEndGoal(e.target.value)}
                  placeholder="Describe what you want to achieve…"
                  rows={3}
                />
              </div>

              <div className="space-y-2">
                <Label>Short title (optional)</Label>
                <Input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Summer cut"
                />
              </div>

              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep(0)}>Back</Button>
                <Button className="flex-1" onClick={() => {
                  const parsed = parseDateFromText(endGoal)
                  if (parsed && !targetDate) setTargetDate(parsed)
                  const nutrition = parseNutritionFromText(endGoal)
                  if (nutrition.calories) setTargetCalories(String(nutrition.calories))
                  if (nutrition.protein) setTargetProtein(String(nutrition.protein))
                  setStep(2)
                }} disabled={!endGoal.trim()}>
                  Continue
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {step === 2 && (
          <Card>
            <CardHeader>
              <CardTitle>About you & your targets</CardTitle>
              <CardDescription>Gender and age help us estimate calories and personalize your plan</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>Gender</Label>
                  <Select
                    value={gender}
                    onChange={(e) => setGender(e.target.value as Gender | '')}
                  >
                    <option value="">Select gender</option>
                    {genderOptions.map(({ value, label }) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Age</Label>
                  <Input
                    type="number"
                    min={0}
                    max={100}
                    value={age}
                    onChange={(e) => setAge(e.target.value)}
                    placeholder="25"
                  />
                </div>
              </div>

              <div className="rounded-xl border border-primary/20 bg-primary/5 p-4">
                <div className="flex items-center gap-2 text-sm font-medium text-primary">
                  <Lightbulb className="h-4 w-4" />
                  {guidanceLoading ? 'Personalizing your plan…' : guidance?.title ?? 'Coaching guidance'}
                </div>
                {guidanceLoading ? (
                  <div className="mt-3 flex justify-center py-2">
                    <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                  </div>
                ) : (
                  <ul className="mt-2 space-y-1 text-body-secondary">
                    {(guidance?.tips ?? []).map((tip) => (
                      <li key={tip}>• {tip}</li>
                    ))}
                  </ul>
                )}
              </div>

              {showWeight && (
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Current weight (kg)</Label>
                    <Input type="number" value={currentWeight} onChange={(e) => setCurrentWeight(e.target.value)} placeholder="75" />
                  </div>
                  <div className="space-y-2">
                    <Label>Target weight (kg)</Label>
                    <Input type="number" value={targetWeight} onChange={(e) => setTargetWeight(e.target.value)} placeholder="70" />
                  </div>
                </div>
              )}

              {showBodyFat && (
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Current body fat (%)</Label>
                    <Input type="number" value={currentBodyFat} onChange={(e) => setCurrentBodyFat(e.target.value)} placeholder="20" />
                  </div>
                  <div className="space-y-2">
                    <Label>Target body fat (%)</Label>
                    <Input type="number" value={targetBodyFat} onChange={(e) => setTargetBodyFat(e.target.value)} placeholder="12" />
                  </div>
                </div>
              )}

              {showStrength && (
                <>
                  <div className="space-y-2">
                    <Label>Target exercise</Label>
                    <Input value={targetExercise} onChange={(e) => setTargetExercise(e.target.value)} placeholder="e.g. Bench Press" />
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label>Current max (kg)</Label>
                      <Input type="number" value={currentLift} onChange={(e) => setCurrentLift(e.target.value)} placeholder="80" />
                    </div>
                    <div className="space-y-2">
                      <Label>Target max (kg)</Label>
                      <Input type="number" value={targetLift} onChange={(e) => setTargetLift(e.target.value)} placeholder="100" />
                    </div>
                  </div>
                </>
              )}

              <div className="space-y-2">
                <Label>Goal deadline (optional)</Label>
                <Input
                  type="date"
                  min={minDateStr}
                  value={targetDate}
                  onChange={(e) => setTargetDate(e.target.value)}
                />
                <p className="text-meta">
                  Fill in your targets, then click Start coaching — we'll analyze your full plan in one go.
                </p>
              </div>

              {!planLoading && hasAssessment && (
                <GoalPlanAssessment
                  feasibility={feasibility!}
                  weeksUntilDeadline={weeksUntilDeadline}
                  needsAck={needsExtremeAck}
                  acknowledged={acknowledgedExtreme}
                  onAckChange={setAcknowledgedExtreme}
                />
              )}

              {planLoading && (
                <div className="flex items-center gap-2 text-meta">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                  Analyzing your plan…
                </div>
              )}

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>Daily calorie target</Label>
                  <Input
                    type="number"
                    value={targetCalories}
                    onChange={(e) => setTargetCalories(e.target.value)}
                    placeholder="Auto from AI after analysis"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Daily protein target (g)</Label>
                  <Input
                    type="number"
                    value={targetProtein}
                    onChange={(e) => setTargetProtein(e.target.value)}
                    placeholder="Auto from AI after analysis"
                  />
                </div>
              </div>

              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep(1)}>Back</Button>
                <Button
                  className="flex-1"
                  onClick={handleSubmit}
                  disabled={!profileComplete || loading || planLoading || (planAnalyzed && needsExtremeAck && !acknowledgedExtreme)}
                >
                  {!profileComplete ? 'Enter gender and age to continue' : submitLabel}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
