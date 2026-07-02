import { useCallback, useEffect, useState } from 'react'
import { Plus, Trash2, HeartPulse } from 'lucide-react'
import { api, Workout, SetCreate, ActivityLog } from '@/lib/api'
import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { ScrollReveal, revealDelay } from '@/components/ScrollReveal'
import { Input, Label, Textarea } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDate, todayISO } from '@/lib/utils'

interface ExerciseForm {
  exercise_name: string
  sets: SetCreate[]
}

export function WorkoutsPage() {
  const [viewDate, setViewDate] = useState(todayISO())
  const [workouts, setWorkouts] = useState<Workout[]>([])
  const [cardioLogs, setCardioLogs] = useState<ActivityLog[]>([])
  const [showForm, setShowForm] = useState(false)
  const [showCardioForm, setShowCardioForm] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [savingCardio, setSavingCardio] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [deletingCardioId, setDeletingCardioId] = useState<number | null>(null)

  const [workoutDate, setWorkoutDate] = useState(todayISO())
  const [workoutName, setWorkoutName] = useState('')
  const [notes, setNotes] = useState('')
  const [exercises, setExercises] = useState<ExerciseForm[]>([
    { exercise_name: '', sets: [{ set_number: 1, weight_kg: undefined, reps: undefined, rest_seconds: 60 }] },
  ])

  const [cardioDate, setCardioDate] = useState(todayISO())
  const [cardioType, setCardioType] = useState('')
  const [cardioDuration, setCardioDuration] = useState('')

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
    setExercises([...exercises, {
      exercise_name: '',
      sets: [{ set_number: 1, weight_kg: undefined, reps: undefined, rest_seconds: 60 }],
    }])
  }

  const addSet = (exIdx: number) => {
    const updated = [...exercises]
    const setNum = updated[exIdx].sets.length + 1
    updated[exIdx].sets.push({ set_number: setNum, weight_kg: undefined, reps: undefined, rest_seconds: 60 })
    setExercises(updated)
  }

  const updateExercise = (exIdx: number, field: string, value: string) => {
    const updated = [...exercises]
    updated[exIdx] = { ...updated[exIdx], [field]: value }
    setExercises(updated)
  }

  const updateSet = (exIdx: number, setIdx: number, field: string, value: string) => {
    const updated = [...exercises]
    updated[exIdx].sets[setIdx] = {
      ...updated[exIdx].sets[setIdx],
      [field]: value ? parseFloat(value) : undefined,
    }
    setExercises(updated)
  }

  const removeExercise = (exIdx: number) => {
    setExercises(exercises.filter((_, i) => i !== exIdx))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const workout = await api.createWorkout({
        workout_date: workoutDate,
        name: workoutName || undefined,
        notes: notes || undefined,
        exercises: exercises.filter(e => e.exercise_name).map((ex, i) => ({
          exercise_name: ex.exercise_name,
          order_index: i,
          sets: ex.sets.map(s => ({
            set_number: s.set_number,
            weight_kg: s.weight_kg,
            reps: s.reps,
            rest_seconds: s.rest_seconds,
          })),
        })),
      })
      if (workout.workout_date === viewDate) {
        setWorkouts([workout, ...workouts])
      } else {
        await loadDay(viewDate)
      }
      setShowForm(false)
      setExercises([{ exercise_name: '', sets: [{ set_number: 1, rest_seconds: 60 }] }])
      setWorkoutName('')
      setNotes('')
    } catch (err) {
      console.error(err)
    } finally {
      setSaving(false)
    }
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
                  <div className="flex items-center gap-2">
                    <Input
                      value={ex.exercise_name}
                      onChange={(e) => updateExercise(exIdx, 'exercise_name', e.target.value)}
                      placeholder="Exercise name (e.g. Preacher Curl)"
                      className="flex-1"
                    />
                    {exercises.length > 1 && (
                      <Button type="button" variant="ghost" size="sm" onClick={() => removeExercise(exIdx)}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    )}
                  </div>

                  <div className="space-y-2">
                    <div className="space-y-3 md:hidden">
                      {ex.sets.map((set, setIdx) => (
                        <div key={setIdx} className="rounded-lg border border-border bg-muted/30 p-3 space-y-2">
                          <p className="text-sm font-medium">Set {set.set_number}</p>
                          <div className="grid grid-cols-2 gap-2">
                            <div className="space-y-1">
                              <span className="text-label text-[0.75rem] normal-case">Weight (kg)</span>
                              <Input type="number" step="0.5" placeholder="15" value={set.weight_kg ?? ''} onChange={(e) => updateSet(exIdx, setIdx, 'weight_kg', e.target.value)} />
                            </div>
                            <div className="space-y-1">
                              <span className="text-label text-[0.75rem] normal-case">Reps</span>
                              <Input type="number" placeholder="10" value={set.reps ?? ''} onChange={(e) => updateSet(exIdx, setIdx, 'reps', e.target.value)} />
                            </div>
                            <div className="space-y-1 col-span-2">
                              <span className="text-label text-[0.75rem] normal-case">Rest (seconds)</span>
                              <Input type="number" placeholder="60" value={set.rest_seconds ?? ''} onChange={(e) => updateSet(exIdx, setIdx, 'rest_seconds', e.target.value)} />
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="hidden md:block space-y-2">
                      <div className="grid grid-cols-5 gap-2 text-label text-[0.75rem] normal-case px-1">
                        <span>Set</span><span>Weight (kg)</span><span>Reps</span><span>Rest (s)</span><span></span>
                      </div>
                      {ex.sets.map((set, setIdx) => (
                        <div key={setIdx} className="grid grid-cols-5 gap-2">
                          <Input value={set.set_number} disabled className="text-center" />
                          <Input type="number" step="0.5" placeholder="15" value={set.weight_kg ?? ''} onChange={(e) => updateSet(exIdx, setIdx, 'weight_kg', e.target.value)} />
                          <Input type="number" placeholder="10" value={set.reps ?? ''} onChange={(e) => updateSet(exIdx, setIdx, 'reps', e.target.value)} />
                          <Input type="number" placeholder="60" value={set.rest_seconds ?? ''} onChange={(e) => updateSet(exIdx, setIdx, 'rest_seconds', e.target.value)} />
                          <span />
                        </div>
                      ))}
                    </div>
                    <Button type="button" variant="ghost" size="sm" onClick={() => addSet(exIdx)}>+ Add set</Button>
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
                <Button type="button" variant="outline" onClick={() => setShowForm(false)} className="w-full sm:w-auto">Cancel</Button>
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
                            {s.weight_kg ? `${s.weight_kg}kg × ` : ''}{s.reps ?? '?'} reps
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
                <Button type="button" variant="outline" onClick={() => setShowCardioForm(false)} className="w-full sm:w-auto">Cancel</Button>
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
