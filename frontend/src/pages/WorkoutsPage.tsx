import { useCallback, useEffect, useState } from 'react'
import { Plus, Trash2, HeartPulse } from 'lucide-react'
import { api, Workout, SetCreate, ActivityLog } from '@/lib/api'
import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { ScrollReveal, revealDelay } from '@/components/ScrollReveal'
import { Input, Label, Textarea } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDate, todayISO } from '@/lib/utils'
import { formatExerciseSet, repUnit } from '@/lib/exerciseDisplay'
import { useLocalDraft, loadDraft, clearDraft } from '@/hooks/useLocalDraft'

interface ComboMember {
  exercise_name: string
  sets: SetCreate[]
}

interface ExerciseForm {
  isCombo: boolean
  members: ComboMember[]
}

function blankSet(setNumber: number): SetCreate {
  return { set_number: setNumber, weight_kg: undefined, reps: undefined, rest_seconds: 60 }
}

const WORKOUT_DRAFT_KEY = 'fitai_workout_draft'
const CARDIO_DRAFT_KEY = 'fitai_cardio_draft'

interface WorkoutDraft {
  workoutDate: string
  workoutName: string
  notes: string
  exercises: ExerciseForm[]
}

interface CardioDraft {
  cardioDate: string
  cardioType: string
  cardioDuration: string
}

function isValidWorkoutDraft(draft: WorkoutDraft | null): draft is WorkoutDraft {
  return Boolean(
    draft &&
      Array.isArray(draft.exercises) &&
      draft.exercises.every(
        (ex) => ex && Array.isArray(ex.members) && ex.members.length > 0 && typeof ex.members[0].exercise_name === 'string',
      ),
  )
}

export function WorkoutsPage() {
  const [viewDate, setViewDate] = useState(todayISO())
  const [workouts, setWorkouts] = useState<Workout[]>([])
  const [cardioLogs, setCardioLogs] = useState<ActivityLog[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [savingCardio, setSavingCardio] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [deletingCardioId, setDeletingCardioId] = useState<number | null>(null)

  const blankExercise = (): ExerciseForm => ({
    isCombo: false,
    members: [{ exercise_name: '', sets: [blankSet(1)] }],
  })

  const rawWorkoutDraft = loadDraft<WorkoutDraft>(WORKOUT_DRAFT_KEY)
  const workoutDraft = isValidWorkoutDraft(rawWorkoutDraft) ? rawWorkoutDraft : null
  if (rawWorkoutDraft && !workoutDraft) clearDraft(WORKOUT_DRAFT_KEY)
  const cardioDraft = loadDraft<CardioDraft>(CARDIO_DRAFT_KEY)

  const [workoutDate, setWorkoutDate] = useState(workoutDraft?.workoutDate ?? todayISO())
  const [workoutName, setWorkoutName] = useState(workoutDraft?.workoutName ?? '')
  const [notes, setNotes] = useState(workoutDraft?.notes ?? '')
  const [exercises, setExercises] = useState<ExerciseForm[]>(
    workoutDraft?.exercises ?? [blankExercise()],
  )
  const [showForm, setShowForm] = useState(Boolean(workoutDraft))

  const [cardioDate, setCardioDate] = useState(cardioDraft?.cardioDate ?? todayISO())
  const [cardioType, setCardioType] = useState(cardioDraft?.cardioType ?? '')
  const [cardioDuration, setCardioDuration] = useState(cardioDraft?.cardioDuration ?? '')
  const [showCardioForm, setShowCardioForm] = useState(Boolean(cardioDraft))

  useLocalDraft(WORKOUT_DRAFT_KEY, { workoutDate, workoutName, notes, exercises }, showForm)
  useLocalDraft(CARDIO_DRAFT_KEY, { cardioDate, cardioType, cardioDuration }, showCardioForm)

  const loadDay = useCallback(async (date: string) => {
    const [w, c] = await Promise.all([
      api.getWorkouts({ workoutDate: date }),
      api.getActivities({ category: 'cardio', logDate: date }),
    ])
    setWorkouts(w)
    setCardioLogs(c)
  }, [])

  useEffect(() => {
    loadDay(viewDate).catch(console.error).finally(() => setLoading(false))
  }, [loadDay, viewDate])

  const handleViewDateChange = (date: string) => {
    setViewDate(date)
    setWorkoutDate(date)
    setCardioDate(date)
    setLoading(true)
    loadDay(date).catch(console.error).finally(() => setLoading(false))
  }

  const addExercise = () => {
    setExercises([...exercises, blankExercise()])
  }

  const removeExercise = (exIdx: number) => {
    setExercises(exercises.filter((_, i) => i !== exIdx))
  }

  const updateMemberName = (exIdx: number, memberIdx: number, value: string) => {
    const updated = [...exercises]
    const members = [...updated[exIdx].members]
    members[memberIdx] = { ...members[memberIdx], exercise_name: value }
    updated[exIdx] = { ...updated[exIdx], members }
    setExercises(updated)
  }

  const roundCountFor = (ex: ExerciseForm) => ex.members[0]?.sets.length ?? 1

  const toggleCombo = (exIdx: number) => {
    const updated = [...exercises]
    const ex = updated[exIdx]
    if (ex.members.length > 1) {
      updated[exIdx] = { ...ex, isCombo: true }
    } else {
      const rounds = roundCountFor(ex)
      updated[exIdx] = {
        ...ex,
        isCombo: true,
        members: [...ex.members, { exercise_name: '', sets: Array.from({ length: rounds }, (_, i) => blankSet(i + 1)) }],
      }
    }
    setExercises(updated)
  }

  const removeCombo = (exIdx: number) => {
    const updated = [...exercises]
    updated[exIdx] = { ...updated[exIdx], isCombo: false, members: [updated[exIdx].members[0]] }
    setExercises(updated)
  }

  const addComboMember = (exIdx: number) => {
    const updated = [...exercises]
    const ex = updated[exIdx]
    const rounds = roundCountFor(ex)
    updated[exIdx] = {
      ...ex,
      members: [...ex.members, { exercise_name: '', sets: Array.from({ length: rounds }, (_, i) => blankSet(i + 1)) }],
    }
    setExercises(updated)
  }

  const removeComboMember = (exIdx: number, memberIdx: number) => {
    const updated = [...exercises]
    const remaining = updated[exIdx].members.filter((_, i) => i !== memberIdx)
    updated[exIdx] = { ...updated[exIdx], isCombo: remaining.length > 1, members: remaining }
    setExercises(updated)
  }

  const addRound = (exIdx: number) => {
    const updated = [...exercises]
    updated[exIdx] = {
      ...updated[exIdx],
      members: updated[exIdx].members.map(m => ({ ...m, sets: [...m.sets, blankSet(m.sets.length + 1)] })),
    }
    setExercises(updated)
  }

  const removeRound = (exIdx: number, roundIdx: number) => {
    const updated = [...exercises]
    updated[exIdx] = {
      ...updated[exIdx],
      members: updated[exIdx].members.map(m => ({
        ...m,
        sets: m.sets.filter((_, i) => i !== roundIdx).map((s, i) => ({ ...s, set_number: i + 1 })),
      })),
    }
    setExercises(updated)
  }

  const updateMemberSet = (exIdx: number, memberIdx: number, roundIdx: number, field: string, value: string) => {
    const updated = [...exercises]
    const members = [...updated[exIdx].members]
    const sets = [...members[memberIdx].sets]
    sets[roundIdx] = { ...sets[roundIdx], [field]: value ? parseFloat(value) : undefined }
    members[memberIdx] = { ...members[memberIdx], sets }
    updated[exIdx] = { ...updated[exIdx], members }
    setExercises(updated)
  }

  /** Combo rest is a single value shared by every member exercise's set for that round. */
  const updateRoundRest = (exIdx: number, roundIdx: number, value: string) => {
    const updated = [...exercises]
    const restValue = value ? parseFloat(value) : undefined
    updated[exIdx] = {
      ...updated[exIdx],
      members: updated[exIdx].members.map((m) => {
        const sets = [...m.sets]
        sets[roundIdx] = { ...sets[roundIdx], rest_seconds: restValue }
        return { ...m, sets }
      }),
    }
    setExercises(updated)
  }

  const addDropStage = (exIdx: number, memberIdx: number, roundIdx: number) => {
    const updated = [...exercises]
    const members = [...updated[exIdx].members]
    const sets = [...members[memberIdx].sets]
    const set = sets[roundIdx]
    const stages = set.drop_stages ?? []
    sets[roundIdx] = {
      ...set,
      drop_stages: [...stages, { stage_number: stages.length + 2, weight_kg: undefined, reps: undefined }],
    }
    members[memberIdx] = { ...members[memberIdx], sets }
    updated[exIdx] = { ...updated[exIdx], members }
    setExercises(updated)
  }

  const updateDropStage = (
    exIdx: number,
    memberIdx: number,
    roundIdx: number,
    stageIdx: number,
    field: 'weight_kg' | 'reps',
    value: string,
  ) => {
    const updated = [...exercises]
    const members = [...updated[exIdx].members]
    const sets = [...members[memberIdx].sets]
    const set = sets[roundIdx]
    const stages = [...(set.drop_stages ?? [])]
    stages[stageIdx] = { ...stages[stageIdx], [field]: value ? parseFloat(value) : undefined }
    sets[roundIdx] = { ...set, drop_stages: stages }
    members[memberIdx] = { ...members[memberIdx], sets }
    updated[exIdx] = { ...updated[exIdx], members }
    setExercises(updated)
  }

  const removeDropStage = (exIdx: number, memberIdx: number, roundIdx: number, stageIdx: number) => {
    const updated = [...exercises]
    const members = [...updated[exIdx].members]
    const sets = [...members[memberIdx].sets]
    const set = sets[roundIdx]
    const stages = (set.drop_stages ?? [])
      .filter((_, i) => i !== stageIdx)
      .map((s, i) => ({ ...s, stage_number: i + 2 }))
    sets[roundIdx] = { ...set, drop_stages: stages }
    members[memberIdx] = { ...members[memberIdx], sets }
    updated[exIdx] = { ...updated[exIdx], members }
    setExercises(updated)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const workout = await api.createWorkout({
        workout_date: workoutDate,
        name: workoutName || undefined,
        notes: notes || undefined,
        exercises: exercises
          .flatMap(ex => ex.members.filter(m => m.exercise_name.trim()))
          .map((member, i) => ({
            exercise_name: member.exercise_name,
            order_index: i,
            sets: member.sets.map(s => ({
              set_number: s.set_number,
              weight_kg: s.weight_kg,
              reps: s.reps,
              rest_seconds: s.rest_seconds,
              drop_stages: s.drop_stages,
            })),
          })),
      })
      if (workout.workout_date === viewDate) {
        setWorkouts([workout, ...workouts])
      } else {
        await loadDay(viewDate)
      }
      setShowForm(false)
      setExercises([blankExercise()])
      setWorkoutName('')
      setNotes('')
      clearDraft(WORKOUT_DRAFT_KEY)
    } catch (err) {
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  const handleCancelWorkoutForm = () => {
    setShowForm(false)
    setExercises([blankExercise()])
    setWorkoutName('')
    setNotes('')
    clearDraft(WORKOUT_DRAFT_KEY)
  }

  const handleCancelCardioForm = () => {
    setShowCardioForm(false)
    setCardioType('')
    setCardioDuration('')
    clearDraft(CARDIO_DRAFT_KEY)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this workout?')) return
    setDeletingId(id)
    try {
      await api.deleteWorkout(id)
      setWorkouts(workouts.filter(w => w.id !== id))
    } catch (err) {
      console.error(err)
    } finally {
      setDeletingId(null)
    }
  }

  const handleCardioSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!cardioType.trim() || !cardioDuration) return
    setSavingCardio(true)
    try {
      const log = await api.createActivity({
        log_date: cardioDate,
        activity_name: cardioType.trim(),
        duration_minutes: parseInt(cardioDuration, 10),
        category: 'cardio',
      })
      if (log.log_date === viewDate) {
        setCardioLogs([log, ...cardioLogs])
      } else {
        await loadDay(viewDate)
      }
      setShowCardioForm(false)
      setCardioType('')
      setCardioDuration('')
      clearDraft(CARDIO_DRAFT_KEY)
    } catch (err) {
      console.error(err)
    } finally {
      setSavingCardio(false)
    }
  }

  const handleDeleteCardio = async (id: number) => {
    if (!confirm('Delete this cardio session?')) return
    setDeletingCardioId(id)
    try {
      await api.deleteActivity(id)
      setCardioLogs(cardioLogs.filter(c => c.id !== id))
    } catch (err) {
      console.error(err)
    } finally {
      setDeletingCardioId(null)
    }
  }

  const gymCalories = workouts.reduce((sum, w) => sum + (w.calories_burned ?? 0), 0)
  const cardioCalories = cardioLogs.reduce((sum, c) => sum + (c.calories_burned ?? 0), 0)
  const totalCalories = gymCalories + cardioCalories

  return (
    <div className="space-y-6">
      <ScrollReveal animation="fade-up">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <PageHeader title="Workouts" subtitle="Log exercises, sets, reps, and weights" />
          <Button onClick={() => setShowForm(!showForm)} className="w-full sm:w-auto">
            <Plus className="h-4 w-4" />
            Log Workout
          </Button>
        </div>
      </ScrollReveal>

      <ScrollReveal animation="blur-up">
        <Card>
          <CardContent className="pt-6 space-y-4">
            <div className="space-y-2">
              <Label>View date</Label>
              <Input
                type="date"
                value={viewDate}
                onChange={(e) => handleViewDateChange(e.target.value)}
              />
              <p className="text-meta">
                Showing workouts and cardio for {formatDate(viewDate)}
              </p>
            </div>
            {(workouts.length > 0 || cardioLogs.length > 0) && (
              <div className="grid gap-3 grid-cols-2 sm:grid-cols-4">
                {[
                  { label: 'Gym sessions', value: workouts.length },
                  { label: 'Cardio sessions', value: cardioLogs.length },
                  { label: 'Gym burn', value: `~${Math.round(gymCalories)} kcal` },
                  { label: 'Total burn', value: `~${Math.round(totalCalories)} kcal` },
                ].map(({ label, value }) => (
                  <div key={label} className="luxury-card rounded-xl p-4 text-center">
                    <p className="text-label">{label}</p>
                    <p className="text-xl font-bold font-display text-foreground">{value}</p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </ScrollReveal>

      {showForm && (
        <ScrollReveal animation="blur-up">
          <Card>
          <CardHeader>
            <CardTitle>New Workout</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>Date</Label>
                  <Input type="date" value={workoutDate} onChange={(e) => setWorkoutDate(e.target.value)} required />
                </div>
                <div className="space-y-2">
                  <Label>Workout name</Label>
                  <Input value={workoutName} onChange={(e) => setWorkoutName(e.target.value)} placeholder="Push Day" />
                </div>
              </div>

              {exercises.map((ex, exIdx) => (
                <div key={exIdx} className="rounded-lg border border-border p-4 space-y-3">
                  {!ex.isCombo ? (
                    <div className="flex items-center gap-2">
                      <Input
                        value={ex.members[0].exercise_name}
                        onChange={(e) => updateMemberName(exIdx, 0, e.target.value)}
                        placeholder="Exercise name (e.g. Preacher Curl)"
                        className="flex-1"
                      />
                      <Button type="button" variant="outline" size="sm" onClick={() => toggleCombo(exIdx)}>
                        Combination exercise
                      </Button>
                      {exercises.length > 1 && (
                        <Button type="button" variant="ghost" size="sm" onClick={() => removeExercise(exIdx)}>
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-2 rounded-lg border border-dashed border-primary/40 p-3">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-label text-[0.75rem] normal-case">
                          Combination exercise — done back-to-back with no rest in between
                        </span>
                        {exercises.length > 1 && (
                          <Button type="button" variant="ghost" size="sm" onClick={() => removeExercise(exIdx)}>
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        )}
                      </div>
                      {ex.members.map((member, memberIdx) => (
                        <div key={memberIdx} className="flex items-center gap-2">
                          <Input
                            value={member.exercise_name}
                            onChange={(e) => updateMemberName(exIdx, memberIdx, e.target.value)}
                            placeholder={memberIdx === 0 ? 'e.g. Incline Bicep Curl' : 'e.g. Hammer Curl'}
                            className="flex-1"
                          />
                          {ex.members.length > 1 && (
                            <Button type="button" variant="ghost" size="sm" onClick={() => removeComboMember(exIdx, memberIdx)} aria-label="Remove exercise from combo">
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          )}
                        </div>
                      ))}
                      <div className="flex flex-wrap gap-2">
                        <Button type="button" variant="ghost" size="sm" onClick={() => addComboMember(exIdx)}>+ Add exercise</Button>
                        <Button type="button" variant="ghost" size="sm" onClick={() => removeCombo(exIdx)}>Remove combination</Button>
                      </div>
                    </div>
                  )}

                  <div className="space-y-2">
                    {!ex.isCombo ? (
                      <>
                        <div className="space-y-3 md:hidden">
                          {ex.members[0].sets.map((set, roundIdx) => (
                            <div key={roundIdx} className="rounded-lg border border-border bg-muted/30 p-3 space-y-2">
                              <div className="flex items-center justify-between">
                                <p className="text-sm font-medium">Set {set.set_number}</p>
                                {ex.members[0].sets.length > 1 && (
                                  <Button type="button" variant="ghost" size="sm" onClick={() => removeRound(exIdx, roundIdx)} aria-label="Delete set">
                                    <Trash2 className="h-4 w-4 text-destructive" />
                                  </Button>
                                )}
                              </div>
                              <div className="grid grid-cols-2 gap-2">
                                <div className="space-y-1">
                                  <span className="text-label text-[0.75rem] normal-case">Weight (kg)</span>
                                  <Input type="number" step="0.5" placeholder="15" value={set.weight_kg ?? ''} onChange={(e) => updateMemberSet(exIdx, 0, roundIdx, 'weight_kg', e.target.value)} />
                                </div>
                                <div className="space-y-1">
                                  <span className="text-label text-[0.75rem] normal-case">{repUnit(ex.members[0].exercise_name) === 'rounds' ? 'Rounds' : 'Reps'}</span>
                                  <Input type="number" placeholder="10" value={set.reps ?? ''} onChange={(e) => updateMemberSet(exIdx, 0, roundIdx, 'reps', e.target.value)} />
                                </div>
                                <div className="space-y-1 col-span-2">
                                  <span className="text-label text-[0.75rem] normal-case">Rest (seconds)</span>
                                  <Input type="number" placeholder="60" value={set.rest_seconds ?? ''} onChange={(e) => updateMemberSet(exIdx, 0, roundIdx, 'rest_seconds', e.target.value)} />
                                </div>
                              </div>

                              {(set.drop_stages ?? []).map((stage, stageIdx) => (
                                <div key={stageIdx} className="ml-2 border-l-2 border-primary/30 pl-3 space-y-1">
                                  <div className="flex items-center justify-between">
                                    <span className="text-label text-[0.75rem] normal-case">Drop {stageIdx + 1}</span>
                                    <Button type="button" variant="ghost" size="sm" onClick={() => removeDropStage(exIdx, 0, roundIdx, stageIdx)} aria-label="Remove drop stage">
                                      <Trash2 className="h-3.5 w-3.5 text-destructive" />
                                    </Button>
                                  </div>
                                  <div className="grid grid-cols-2 gap-2">
                                    <Input type="number" step="0.5" placeholder="Weight (kg)" value={stage.weight_kg ?? ''} onChange={(e) => updateDropStage(exIdx, 0, roundIdx, stageIdx, 'weight_kg', e.target.value)} />
                                    <Input type="number" placeholder="Reps" value={stage.reps ?? ''} onChange={(e) => updateDropStage(exIdx, 0, roundIdx, stageIdx, 'reps', e.target.value)} />
                                  </div>
                                </div>
                              ))}
                              <Button type="button" variant="ghost" size="sm" onClick={() => addDropStage(exIdx, 0, roundIdx)}>+ Drop set</Button>
                            </div>
                          ))}
                        </div>

                        <div className="hidden md:block space-y-2">
                          <div className="grid grid-cols-5 gap-2 text-label text-[0.75rem] normal-case px-1">
                            <span>Set</span><span>Weight (kg)</span><span>{repUnit(ex.members[0].exercise_name) === 'rounds' ? 'Rounds' : 'Reps'}</span><span>Rest (s)</span><span></span>
                          </div>
                          {ex.members[0].sets.map((set, roundIdx) => (
                            <div key={roundIdx} className="space-y-1">
                              <div className="grid grid-cols-5 gap-2">
                                <Input value={set.set_number} disabled className="text-center" />
                                <Input type="number" step="0.5" placeholder="15" value={set.weight_kg ?? ''} onChange={(e) => updateMemberSet(exIdx, 0, roundIdx, 'weight_kg', e.target.value)} />
                                <Input type="number" placeholder="10" value={set.reps ?? ''} onChange={(e) => updateMemberSet(exIdx, 0, roundIdx, 'reps', e.target.value)} />
                                <Input type="number" placeholder="60" value={set.rest_seconds ?? ''} onChange={(e) => updateMemberSet(exIdx, 0, roundIdx, 'rest_seconds', e.target.value)} />
                                {ex.members[0].sets.length > 1 ? (
                                  <Button type="button" variant="ghost" size="sm" onClick={() => removeRound(exIdx, roundIdx)} aria-label="Delete set">
                                    <Trash2 className="h-4 w-4 text-destructive" />
                                  </Button>
                                ) : (
                                  <span />
                                )}
                              </div>
                              {(set.drop_stages ?? []).map((stage, stageIdx) => (
                                <div key={stageIdx} className="grid grid-cols-5 gap-2">
                                  <span className="text-meta text-xs flex items-center justify-center">↳ Drop {stageIdx + 1}</span>
                                  <Input type="number" step="0.5" placeholder="Weight" value={stage.weight_kg ?? ''} onChange={(e) => updateDropStage(exIdx, 0, roundIdx, stageIdx, 'weight_kg', e.target.value)} />
                                  <Input type="number" placeholder="Reps" value={stage.reps ?? ''} onChange={(e) => updateDropStage(exIdx, 0, roundIdx, stageIdx, 'reps', e.target.value)} />
                                  <span />
                                  <Button type="button" variant="ghost" size="sm" onClick={() => removeDropStage(exIdx, 0, roundIdx, stageIdx)} aria-label="Remove drop stage">
                                    <Trash2 className="h-4 w-4 text-destructive" />
                                  </Button>
                                </div>
                              ))}
                              <Button type="button" variant="ghost" size="sm" onClick={() => addDropStage(exIdx, 0, roundIdx)}>+ Drop set</Button>
                            </div>
                          ))}
                        </div>
                      </>
                    ) : (
                      <div className="space-y-3">
                        {ex.members[0].sets.map((_, roundIdx) => (
                          <div key={roundIdx} className="rounded-lg border border-border bg-muted/30 p-3 space-y-3">
                            <div className="flex items-center justify-between">
                              <p className="text-sm font-medium">Round {roundIdx + 1}</p>
                              {ex.members[0].sets.length > 1 && (
                                <Button type="button" variant="ghost" size="sm" onClick={() => removeRound(exIdx, roundIdx)} aria-label="Delete round">
                                  <Trash2 className="h-4 w-4 text-destructive" />
                                </Button>
                              )}
                            </div>
                            {ex.members.map((member, memberIdx) => {
                              const set = member.sets[roundIdx]
                              if (!set) return null
                              return (
                                <div key={memberIdx} className="rounded-lg border border-border/60 bg-background/40 p-3 space-y-2">
                                  <p className="text-sm font-medium">
                                    Set {set.set_number} of {member.exercise_name || `Exercise ${memberIdx + 1}`}
                                  </p>
                                  <div className="grid grid-cols-2 gap-2">
                                    <div className="space-y-1">
                                      <span className="text-label text-[0.75rem] normal-case">Weight (kg)</span>
                                      <Input type="number" step="0.5" placeholder="15" value={set.weight_kg ?? ''} onChange={(e) => updateMemberSet(exIdx, memberIdx, roundIdx, 'weight_kg', e.target.value)} />
                                    </div>
                                    <div className="space-y-1">
                                      <span className="text-label text-[0.75rem] normal-case">Reps</span>
                                      <Input type="number" placeholder="10" value={set.reps ?? ''} onChange={(e) => updateMemberSet(exIdx, memberIdx, roundIdx, 'reps', e.target.value)} />
                                    </div>
                                  </div>
                                  {(set.drop_stages ?? []).map((stage, stageIdx) => (
                                    <div key={stageIdx} className="ml-2 border-l-2 border-primary/30 pl-3 space-y-1">
                                      <div className="flex items-center justify-between">
                                        <span className="text-label text-[0.75rem] normal-case">Drop {stageIdx + 1}</span>
                                        <Button type="button" variant="ghost" size="sm" onClick={() => removeDropStage(exIdx, memberIdx, roundIdx, stageIdx)} aria-label="Remove drop stage">
                                          <Trash2 className="h-3.5 w-3.5 text-destructive" />
                                        </Button>
                                      </div>
                                      <div className="grid grid-cols-2 gap-2">
                                        <Input type="number" step="0.5" placeholder="Weight (kg)" value={stage.weight_kg ?? ''} onChange={(e) => updateDropStage(exIdx, memberIdx, roundIdx, stageIdx, 'weight_kg', e.target.value)} />
                                        <Input type="number" placeholder="Reps" value={stage.reps ?? ''} onChange={(e) => updateDropStage(exIdx, memberIdx, roundIdx, stageIdx, 'reps', e.target.value)} />
                                      </div>
                                    </div>
                                  ))}
                                  <Button type="button" variant="ghost" size="sm" onClick={() => addDropStage(exIdx, memberIdx, roundIdx)}>+ Drop set</Button>
                                </div>
                              )
                            })}
                            <div className="space-y-1">
                              <span className="text-label text-[0.75rem] normal-case">Rest after this round (seconds)</span>
                              <Input
                                type="number"
                                placeholder="60"
                                value={ex.members[0].sets[roundIdx]?.rest_seconds ?? ''}
                                onChange={(e) => updateRoundRest(exIdx, roundIdx, e.target.value)}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    <Button type="button" variant="ghost" size="sm" onClick={() => addRound(exIdx)}>+ Add set</Button>
                  </div>
                </div>
              ))}

              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={addExercise}>+ Add exercise</Button>
              </div>

              <div className="space-y-2">
                <Label>Notes</Label>
                <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="How did it feel?" />
              </div>

              <div className="flex flex-col gap-3 sm:flex-row">
                <Button type="button" variant="outline" onClick={handleCancelWorkoutForm} className="w-full sm:w-auto">Cancel</Button>
                <Button type="submit" disabled={saving} className="w-full sm:w-auto">{saving ? 'Saving...' : 'Save workout'}</Button>
              </div>
            </form>
          </CardContent>
          </Card>
        </ScrollReveal>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="luxury-spinner" />
        </div>
      ) : workouts.length === 0 ? (
        <ScrollReveal>
          <Card>
            <CardContent className="py-12 text-center text-empty">
              No gym workouts logged for {formatDate(viewDate)}.
            </CardContent>
          </Card>
        </ScrollReveal>
      ) : (
        <div className="space-y-4">
          {workouts.map((w, i) => (
            <ScrollReveal key={w.id} delay={revealDelay(i % 8, 75)} animation="slide-left">
              <Card>
              <CardHeader className="pb-2">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <CardTitle>{w.name || 'Workout'}</CardTitle>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-meta">{formatDate(w.workout_date)}</span>
                    {(w.calories_burned ?? 0) > 0 && (
                      <span className="rounded-md bg-primary/15 px-2.5 py-1 text-sm font-semibold text-primary">
                        ~{Math.round(w.calories_burned ?? 0)} kcal burned
                      </span>
                    )}
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(w.id)}
                      disabled={deletingId === w.id}
                      aria-label="Delete workout"
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {w.exercises.map((ex) => (
                    <div key={ex.id}>
                      <p className="font-semibold text-base text-foreground">{ex.exercise_name}</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {ex.sets.map((s) => (
                          <span key={s.id} className="rounded-lg border border-border/60 bg-secondary/40 px-3 py-1.5 text-sm font-medium text-foreground">
                            {formatExerciseSet(ex.exercise_name, s)}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
              </Card>
            </ScrollReveal>
          ))}
        </div>
      )}

      <ScrollReveal animation="fade-up">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between pt-4 border-t border-border">
        <div>
          <h2 className="text-xl font-semibold">Cardio</h2>
          <p className="text-body-secondary">Log running, cycling, swimming, and other cardio</p>
        </div>
        <Button variant="outline" onClick={() => setShowCardioForm(!showCardioForm)} className="w-full sm:w-auto">
          <HeartPulse className="h-4 w-4" />
          Log Cardio
        </Button>
        </div>
      </ScrollReveal>

      {showCardioForm && (
        <ScrollReveal animation="blur-up">
          <Card>
          <CardHeader>
            <CardTitle>New Cardio Session</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCardioSubmit} className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="space-y-2">
                  <Label>Date</Label>
                  <Input type="date" value={cardioDate} onChange={(e) => setCardioDate(e.target.value)} required />
                </div>
                <div className="space-y-2">
                  <Label>Activity type</Label>
                  <Input
                    value={cardioType}
                    onChange={(e) => setCardioType(e.target.value)}
                    placeholder="e.g. Running, Cycling, Swimming"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label>Duration (minutes)</Label>
                  <Input
                    type="number"
                    min={1}
                    value={cardioDuration}
                    onChange={(e) => setCardioDuration(e.target.value)}
                    placeholder="30"
                    required
                  />
                </div>
              </div>
              <div className="flex flex-col gap-3 sm:flex-row">
                <Button type="button" variant="outline" onClick={handleCancelCardioForm} className="w-full sm:w-auto">Cancel</Button>
                <Button type="submit" disabled={savingCardio} className="w-full sm:w-auto">
                  {savingCardio ? 'Saving...' : 'Save cardio'}
                </Button>
              </div>
            </form>
          </CardContent>
          </Card>
        </ScrollReveal>
      )}

      {loading ? null : cardioLogs.length === 0 ? (
        <ScrollReveal>
          <Card>
            <CardContent className="py-8 text-center text-empty">
              No cardio logged for {formatDate(viewDate)}.
            </CardContent>
          </Card>
        </ScrollReveal>
      ) : (
        <div className="space-y-3">
          {cardioLogs.map((c, i) => (
            <ScrollReveal key={c.id} delay={revealDelay(i % 6, 75)} animation="slide-right">
              <Card>
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-foreground">{c.activity_name}</p>
                    <p className="text-meta">
                      {formatDate(c.log_date)} · {c.duration_minutes} min
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {(c.calories_burned ?? 0) > 0 && (
                      <span className="rounded-md bg-accent/15 px-2.5 py-1 text-sm font-semibold text-accent">
                        ~{Math.round(c.calories_burned)} kcal
                      </span>
                    )}
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteCardio(c.id)}
                      disabled={deletingCardioId === c.id}
                      aria-label="Delete cardio session"
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              </CardContent>
              </Card>
            </ScrollReveal>
          ))}
        </div>
      )}
    </div>
  )
}
