import { useEffect, useState } from 'react'
import { Sparkles, Trash2 } from 'lucide-react'
import { api, DietLog } from '@/lib/api'
import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { Input, Label, Select, Textarea } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDate, todayISO } from '@/lib/utils'

export function DietPage() {
  const [logs, setLogs] = useState<DietLog[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [logDate, setLogDate] = useState(todayISO())
  const [mealType, setMealType] = useState('lunch')
  const [foodInput, setFoodInput] = useState('')
  const [deletingId, setDeletingId] = useState<number | null>(null)

  useEffect(() => {
    api.getDietLogs().then(setLogs).catch(console.error).finally(() => setLoading(false))
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!foodInput.trim()) return
    setSaving(true)
    try {
      const log = await api.logDiet({ log_date: logDate, meal_type: mealType, food_input: foodInput })
      setLogs([log, ...logs.filter(l => l.id !== log.id)])
      setFoodInput('')
    } catch (err) {
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this meal log?')) return
    setDeletingId(id)
    try {
      await api.deleteDietLog(id)
      setLogs(logs.filter(l => l.id !== id))
    } catch (err) {
      console.error(err)
    } finally {
      setDeletingId(null)
    }
  }

  const todayLogs = logs.filter(l => l.log_date === todayISO())
  const todayTotals = todayLogs.reduce(
    (acc, l) => ({
      calories: acc.calories + l.total_calories,
      protein: acc.protein + l.total_protein,
      carbs: acc.carbs + l.total_carbs,
      fat: acc.fat + l.total_fat,
    }),
    { calories: 0, protein: 0, carbs: 0, fat: 0 }
  )

  return (
    <div className="space-y-6">
      <PageHeader title="Diet Log" subtitle="Type what you ate — AI estimates the macros" />

      {/* Today's summary */}
      <div className="grid gap-3 grid-cols-2 sm:grid-cols-4">
        {[
          { label: 'Calories', value: Math.round(todayTotals.calories), unit: 'kcal' },
          { label: 'Protein', value: Math.round(todayTotals.protein), unit: 'g' },
          { label: 'Carbs', value: Math.round(todayTotals.carbs), unit: 'g' },
          { label: 'Fat', value: Math.round(todayTotals.fat), unit: 'g' },
        ].map(({ label, value, unit }, i) => (
          <div key={label} className={`luxury-card rounded-xl p-4 text-center animate-fade-up stagger-${Math.min(i + 1, 8)}`}>
            <p className="text-[11px] uppercase tracking-wider text-muted-foreground">{label}</p>
            <p className="text-2xl font-bold font-display gradient-text-subtle">
              {value}<span className="text-sm font-normal text-muted-foreground ml-1">{unit}</span>
            </p>
          </div>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            Log a meal
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Date</Label>
                <Input type="date" value={logDate} onChange={(e) => setLogDate(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Meal</Label>
                <Select value={mealType} onChange={(e) => setMealType(e.target.value)}>
                  <option value="breakfast">Breakfast</option>
                  <option value="lunch">Lunch</option>
                  <option value="dinner">Dinner</option>
                  <option value="snack">Snack</option>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label>What did you eat?</Label>
              <Textarea
                value={foodInput}
                onChange={(e) => setFoodInput(e.target.value)}
                placeholder="e.g. 2 rotis + dal + 150g paneer"
                rows={3}
              />
              <p className="text-xs text-muted-foreground">
                Gemini estimates calories and macros from your description.
              </p>
            </div>
            <Button type="submit" disabled={saving || !foodInput.trim()} className="w-full sm:w-auto">
              {saving ? 'Analyzing...' : 'Log food'}
            </Button>
          </form>
        </CardContent>
      </Card>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="luxury-spinner" />
        </div>
      ) : (
        <div className="space-y-4">
          {logs.map((log) => (
            <Card key={log.id}>
              <CardHeader className="pb-2">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <CardTitle className="text-base capitalize">{log.meal_type || 'Meal'}</CardTitle>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">{formatDate(log.log_date)}</span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(log.id)}
                      disabled={deletingId === log.id}
                      aria-label="Delete meal log"
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y--2">
                  {log.entries.map((entry) => (
                    <div key={entry.id} className="flex flex-col gap-2 rounded-lg bg-muted/50 px-3 py-2 sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0">
                        <p className="text-sm font-medium">{entry.food_name}</p>
                        <p className="text-xs text-muted-foreground">
                          {entry.quantity} {entry.unit}
                          <span className="ml-2 rounded bg-accent/10 px-1.5 py-0.5 text-accent">AI</span>
                        </p>
                      </div>
                      <div className="text-left text-xs sm:text-right shrink-0">
                        <p>{Math.round(entry.calories)} kcal</p>
                        <p className="text-muted-foreground">P:{Math.round(entry.protein_g)}g C:{Math.round(entry.carbs_g)}g F:{Math.round(entry.fat_g)}g</p>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-3 flex flex-col gap-1 border-t border-border pt-3 text-sm sm:flex-row sm:justify-between">
                  <span className="text-muted-foreground">Total</span>
                  <span className="text-sm">
                    {Math.round(log.total_calories)} kcal · P:{Math.round(log.total_protein)}g · C:{Math.round(log.total_carbs)}g · F:{Math.round(log.total_fat)}g
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
