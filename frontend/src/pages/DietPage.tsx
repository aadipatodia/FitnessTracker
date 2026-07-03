import { useCallback, useEffect, useState } from 'react'
import { Sparkles, Trash2 } from 'lucide-react'
import { api, DietLog } from '@/lib/api'
import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { ScrollReveal, revealDelay } from '@/components/ScrollReveal'
import { Input, Label, Select, Textarea } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDate, todayISO } from '@/lib/utils'

function formatMacros(p: number, c: number, f: number, fi: number) {
  return `P:${Math.round(p)}g · C:${Math.round(c)}g · F:${Math.round(f)}g · Fi:${Math.round(fi)}g`
}

export function DietPage() {
  const [viewDate, setViewDate] = useState(todayISO())
  const [logs, setLogs] = useState<DietLog[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [logDate, setLogDate] = useState(todayISO())
  const [mealType, setMealType] = useState('lunch')
  const [foodInput, setFoodInput] = useState('')
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const loadLogs = useCallback(async (date: string) => {
    const data = await api.getDietLogs({ logDate: date })
    setLogs(data)
  }, [])

  useEffect(() => {
    loadLogs(viewDate).catch(console.error).finally(() => setLoading(false))
  }, [loadLogs, viewDate])

  const handleViewDateChange = (date: string) => {
    setViewDate(date)
    setLogDate(date)
    setLoading(true)
    loadLogs(date).catch(console.error).finally(() => setLoading(false))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!foodInput.trim()) return
    setSaving(true)
    try {
      const log = await api.logDiet({ log_date: logDate, meal_type: mealType, food_input: foodInput })
      if (log.log_date === viewDate) {
        setLogs([log, ...logs.filter(l => l.id !== log.id)])
      } else {
        await loadLogs(viewDate)
      }
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

  const dayTotals = logs.reduce(
    (acc, l) => ({
      calories: acc.calories + l.total_calories,
      protein: acc.protein + l.total_protein,
      carbs: acc.carbs + l.total_carbs,
      fat: acc.fat + l.total_fat,
      fibre: acc.fibre + l.total_fibre,
    }),
    { calories: 0, protein: 0, carbs: 0, fat: 0, fibre: 0 }
  )

  return (
    <div className="space-y-6">
      <PageHeader title="Diet Log" subtitle="Type what you ate — FitAI estimates the macros" />

      <ScrollReveal animation="blur-up">
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-2">
              <Label>View date</Label>
              <Input
                type="date"
                value={viewDate}
                onChange={(e) => handleViewDateChange(e.target.value)}
              />
              <p className="text-meta">
                Showing meals and macros for {formatDate(viewDate)}
              </p>
            </div>
          </CardContent>
        </Card>
      </ScrollReveal>

      <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-5">
        {[
          { label: 'Calories', value: Math.round(dayTotals.calories), unit: 'kcal' },
          { label: 'Protein', value: Math.round(dayTotals.protein), unit: 'g' },
          { label: 'Carbs', value: Math.round(dayTotals.carbs), unit: 'g' },
          { label: 'Fat', value: Math.round(dayTotals.fat), unit: 'g' },
          { label: 'Fibre', value: Math.round(dayTotals.fibre), unit: 'g' },
        ].map(({ label, value, unit }, i) => (
          <ScrollReveal key={label} delay={revealDelay(i, 80)} animation="scale">
            <div className="luxury-card rounded-xl p-4 text-center h-full">
              <p className="text-label">{label}</p>
              <p className="text-2xl font-bold font-display text-foreground">
                {value}<span className="text-base font-medium text-secondary-foreground ml-1">{unit}</span>
              </p>
            </div>
          </ScrollReveal>
        ))}
      </div>

      <ScrollReveal animation="blur-up">
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
              <p className="text-meta">
                FitAI estimates calories, macros, and fibre from your description.
              </p>
            </div>
            <Button type="submit" disabled={saving || !foodInput.trim()} className="w-full sm:w-auto">
              {saving ? 'Analyzing...' : 'Log food'}
            </Button>
          </form>
        </CardContent>
        </Card>
      </ScrollReveal>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="luxury-spinner" />
        </div>
      ) : logs.length === 0 ? (
        <ScrollReveal>
          <Card>
            <CardContent className="py-12 text-center text-empty">
              No meals logged for {formatDate(viewDate)}.
            </CardContent>
          </Card>
        </ScrollReveal>
      ) : (
        <div className="space-y-4">
          {logs.map((log, i) => (
            <ScrollReveal key={log.id} delay={revealDelay(i % 6, 70)} animation="fade-up">
              <Card>
              <CardHeader className="pb-2">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <CardTitle className="capitalize">{log.meal_type || 'Meal'}</CardTitle>
                  <div className="flex items-center gap-2">
                    <span className="text-meta">{formatDate(log.log_date)}</span>
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
                <div className="space-y-2">
                  {log.entries.map((entry) => (
                    <div key={entry.id} className="flex flex-col gap-2 rounded-lg bg-muted/50 px-3 py-2.5 sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0">
                        <p className="text-base font-semibold text-foreground">{entry.food_name}</p>
                        <p className="text-meta">
                          {entry.quantity} {entry.unit}
                          <span className="ml-2 rounded bg-accent/15 px-1.5 py-0.5 text-accent font-medium">AI</span>
                        </p>
                      </div>
                      <div className="text-left text-sm sm:text-right shrink-0">
                        <p className="font-semibold text-foreground">{Math.round(entry.calories)} kcal</p>
                        <p className="text-meta">
                          {formatMacros(entry.protein_g, entry.carbs_g, entry.fat_g, entry.fibre_g ?? 0)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-3 flex flex-col gap-1 border-t border-border pt-3 text-base sm:flex-row sm:justify-between">
                  <span className="text-label normal-case">Total</span>
                  <span className="font-semibold text-foreground">
                    {Math.round(log.total_calories)} kcal · {formatMacros(log.total_protein, log.total_carbs, log.total_fat, log.total_fibre ?? 0)}
                  </span>
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
