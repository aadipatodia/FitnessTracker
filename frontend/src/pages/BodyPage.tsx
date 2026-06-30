import { useEffect, useState } from 'react'
import { Trash2 } from 'lucide-react'
import { api, BodyMetric } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input, Label, Textarea } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDate, todayISO } from '@/lib/utils'

export function BodyPage() {
  const [metrics, setMetrics] = useState<BodyMetric[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [recordedDate, setRecordedDate] = useState(todayISO())
  const [weight, setWeight] = useState('')
  const [bodyFat, setBodyFat] = useState('')
  const [notes, setNotes] = useState('')
  const [deletingId, setDeletingId] = useState<number | null>(null)

  useEffect(() => {
    api.getBodyMetrics().then(setMetrics).catch(console.error).finally(() => setLoading(false))
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const metric = await api.createBodyMetric({
        recorded_date: recordedDate,
        weight_kg: weight ? parseFloat(weight) : undefined,
        body_fat_percent: bodyFat ? parseFloat(bodyFat) : undefined,
        notes: notes || undefined,
      })
      setMetrics([metric, ...metrics])
      setWeight('')
      setBodyFat('')
      setNotes('')
    } catch (err) {
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this body metric log?')) return
    setDeletingId(id)
    try {
      await api.deleteBodyMetric(id)
      setMetrics(metrics.filter(m => m.id !== id))
    } catch (err) {
      console.error(err)
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Body Metrics</h1>
        <p className="text-muted-foreground">Track weight and body fat over time</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Log metrics</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label>Date</Label>
              <Input type="date" value={recordedDate} onChange={(e) => setRecordedDate(e.target.value)} />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Weight (kg)</Label>
                <Input type="number" step="0.1" value={weight} onChange={(e) => setWeight(e.target.value)} placeholder="75.5" />
              </div>
              <div className="space-y-2">
                <Label>Body fat (%)</Label>
                <Input type="number" step="0.1" value={bodyFat} onChange={(e) => setBodyFat(e.target.value)} placeholder="18.5" />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Optional notes" />
            </div>
            <Button type="submit" disabled={saving}>{saving ? 'Saving...' : 'Save metrics'}</Button>
          </form>
        </CardContent>
      </Card>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : metrics.length === 0 ? (
        <Card><CardContent className="py-12 text-center text-muted-foreground">No metrics logged yet.</CardContent></Card>
      ) : (
        <div className="space-y-3">
          {metrics.map((m) => (
            <Card key={m.id}>
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{formatDate(m.recorded_date)}</span>
                  <div className="flex items-center gap-4">
                    <div className="flex gap-4 text-sm">
                      {m.weight_kg && <span>{m.weight_kg} kg</span>}
                      {m.body_fat_percent && <span>{m.body_fat_percent}% BF</span>}
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(m.id)}
                      disabled={deletingId === m.id}
                      aria-label="Delete body metric"
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
                {m.notes && <p className="mt-2 text-sm text-muted-foreground">{m.notes}</p>}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
