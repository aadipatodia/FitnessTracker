import { useEffect, useState } from 'react'
import { Plus, Trash2, HeartPulse } from 'lucide-react'
import { api, Workout, SetCreate, ActivityLog } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input, Label, Textarea } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDate, todayISO } from '@/lib/utils'

interface ExerciseForm {
  exercise_name: string
  sets: SetCreate[]
}

export function WorkoutsPage() {
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

  useEffect(() => {
    Promise.all([
      api.getWorkouts(),
      api.getActivities({ category: 'cardio', limit: 30 }),
    ])
      .then(([w, c]) => { setWorkouts(w); setCardioLogs(c) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

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
      setWorkouts([workout, ...workouts])
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
      setCardioLogs([log, ...cardioLogs])
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Workouts</h1>
          <p className="text-muted-foreground">Log exercises, sets, reps, and weights</p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>
          <Plus className="h-4 w-4" />
          Log Workout
        </Button>
      </div>

      {showForm && (
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
                    <div className="grid grid-cols-5 gap-2 text-xs text-muted-foreground px-1">
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

              <div className="flex gap-3">
                <Button type="button" variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
                <Button type="submit" disabled={saving}>{saving ? 'Saving...' : 'Save workout'}</Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : workouts.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No workouts logged yet. Start tracking your training!
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {workouts.map((w) => (
            <Card key={w.id}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">{w.name || 'Workout'}</CardTitle>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">{formatDate(w.workout_date)}</span>
                    {(w.calories_burned ?? 0) > 0 && (
                      <span className="rounded-md bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
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
                      <p className="font-medium text-sm">{ex.exercise_name}</p>
                      <div className="mt-1 flex flex-wrap gap-2">
                        {ex.sets.map((s) => (
                          <span key={s.id} className="rounded-md bg-muted px-2 py-1 text-xs">
                            {s.weight_kg ? `${s.weight_kg}kg × ` : ''}{s.reps ?? '?'} reps
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between pt-4 border-t border-border">
        <div>
          <h2 className="text-xl font-semibold">Cardio</h2>
          <p className="text-sm text-muted-foreground">Log running, cycling, swimming, and other cardio</p>
        </div>
        <Button variant="outline" onClick={() => setShowCardioForm(!showCardioForm)}>
          <HeartPulse className="h-4 w-4" />
          Log Cardio
        </Button>
      </div>

      {showCardioForm && (
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
              <div className="flex gap-3">
                <Button type="button" variant="outline" onClick={() => setShowCardioForm(false)}>Cancel</Button>
                <Button type="submit" disabled={savingCardio}>
                  {savingCardio ? 'Saving...' : 'Save cardio'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {cardioLogs.length > 0 && (
        <div className="space-y-3">
          {cardioLogs.map((c) => (
            <Card key={c.id}>
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{c.activity_name}</p>
                    <p className="text-sm text-muted-foreground">
                      {formatDate(c.log_date)} · {c.duration_minutes} min
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {(c.calories_burned ?? 0) > 0 && (
                      <span className="rounded-md bg-accent/10 px-2 py-0.5 text-xs font-medium text-accent">
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
          ))}
        </div>
      )}
    </div>
  )
}
