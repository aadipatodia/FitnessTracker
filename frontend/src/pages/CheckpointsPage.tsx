import { useCallback, useEffect, useState } from 'react'
import { Check, Pencil, Plus, Trash2, X } from 'lucide-react'
import { api, Checkpoint, DailyCheckpoints } from '@/lib/api'
import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { ScrollReveal } from '@/components/ScrollReveal'
import { Input, Label } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn, formatDate, todayISO } from '@/lib/utils'

export function CheckpointsPage() {
  const [selectedDate, setSelectedDate] = useState(todayISO())
  const [daily, setDaily] = useState<DailyCheckpoints | null>(null)
  const [templates, setTemplates] = useState<Checkpoint[]>([])
  const [loading, setLoading] = useState(true)
  const [togglingId, setTogglingId] = useState<number | null>(null)
  const [newTitle, setNewTitle] = useState('')
  const [adding, setAdding] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [savingEdit, setSavingEdit] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const loadDaily = useCallback(async (date: string) => {
    const data = await api.getDailyCheckpoints(date)
    setDaily(data)
  }, [])

  const loadTemplates = useCallback(async () => {
    const data = await api.getCheckpoints()
    setTemplates(data)
  }, [])

  useEffect(() => {
    Promise.all([loadDaily(selectedDate), loadTemplates()])
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [loadDaily, loadTemplates, selectedDate])

  const handleDateChange = (date: string) => {
    setSelectedDate(date)
    setLoading(true)
    loadDaily(date).catch(console.error).finally(() => setLoading(false))
  }

  const handleToggle = async (checkpointId: number, completed: boolean) => {
    setTogglingId(checkpointId)
    try {
      const updated = await api.toggleCheckpoint({
        checkpoint_id: checkpointId,
        log_date: selectedDate,
        completed,
      })
      setDaily((prev) => {
        if (!prev) return prev
        const items = prev.items.map((item) =>
          item.id === updated.id ? updated : item
        )
        const completedCount = items.filter((i) => i.completed).length
        return { ...prev, items, completed_count: completedCount }
      })
    } catch (err) {
      console.error(err)
    } finally {
      setTogglingId(null)
    }
  }

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    const title = newTitle.trim()
    if (!title) return
    setAdding(true)
    try {
      const checkpoint = await api.createCheckpoint({ title })
      setTemplates([...templates, checkpoint])
      setNewTitle('')
      await loadDaily(selectedDate)
    } catch (err) {
      console.error(err)
    } finally {
      setAdding(false)
    }
  }

  const startEdit = (checkpoint: Checkpoint) => {
    setEditingId(checkpoint.id)
    setEditTitle(checkpoint.title)
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditTitle('')
  }

  const saveEdit = async (id: number) => {
    const title = editTitle.trim()
    if (!title) return
    setSavingEdit(true)
    try {
      const updated = await api.updateCheckpoint(id, { title })
      setTemplates(templates.map((t) => (t.id === id ? updated : t)))
      setDaily((prev) => {
        if (!prev) return prev
        return {
          ...prev,
          items: prev.items.map((item) =>
            item.id === id ? { ...item, title: updated.title } : item
          ),
        }
      })
      cancelEdit()
    } catch (err) {
      console.error(err)
    } finally {
      setSavingEdit(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this checkpoint? Past completion history for it will also be removed.')) return
    setDeletingId(id)
    try {
      await api.deleteCheckpoint(id)
      setTemplates(templates.filter((t) => t.id !== id))
      setDaily((prev) => {
        if (!prev) return prev
        const items = prev.items.filter((item) => item.id !== id)
        return {
          ...prev,
          items,
          total: items.length,
          completed_count: items.filter((i) => i.completed).length,
        }
      })
    } catch (err) {
      console.error(err)
    } finally {
      setDeletingId(null)
    }
  }

  const progressPercent =
    daily && daily.total > 0 ? Math.round((daily.completed_count / daily.total) * 100) : 0

  return (
    <div className="space-y-6">
      <PageHeader
        title="Daily Checkpoints"
        subtitle="Your checklist items stay the same every day — only checkmarks reset per date"
      />

      <ScrollReveal animation="blur-up">
        <Card>
        <CardHeader>
          <CardTitle>Daily checklist</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Date</Label>
            <Input
              type="date"
              value={selectedDate}
              onChange={(e) => handleDateChange(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Same {templates.length > 0 ? templates.length : ''} checkpoint{templates.length === 1 ? '' : 's'} every day for {formatDate(selectedDate)} — check off what you completed
            </p>
          </div>

          {daily && daily.total > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">
                  {daily.completed_count} of {daily.total} completed
                </span>
                <span className="font-medium text-primary">{progressPercent}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-secondary">
                <div
                  className="h-full rounded-full bg-primary transition-all duration-300"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>
          )}

          {loading ? (
            <div className="flex justify-center py-8">
              <div className="luxury-spinner" />
            </div>
          ) : daily && daily.items.length > 0 ? (
            <ul className="space-y-2">
              {daily.items.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => handleToggle(item.id, !item.completed)}
                    disabled={togglingId === item.id}
                    className={cn(
                      'flex w-full items-center gap-3 rounded-lg border border-border px-4 py-3 text-left transition-colors',
                      item.completed
                        ? 'bg-primary/10 border-primary/30'
                        : 'bg-card hover:bg-secondary/50'
                    )}
                  >
                    <span
                      className={cn(
                        'flex h-6 w-6 shrink-0 items-center justify-center rounded-md border-2 transition-colors',
                        item.completed
                          ? 'border-primary bg-primary text-primary-foreground'
                          : 'border-muted-foreground/40'
                      )}
                    >
                      {item.completed && <Check className="h-4 w-4" />}
                    </span>
                    <span
                      className={cn(
                        'flex-1 font-medium',
                        item.completed && 'text-muted-foreground line-through'
                      )}
                    >
                      {item.title}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No checkpoints yet. Add some below to start tracking your daily habits.
            </p>
          )}
        </CardContent>
        </Card>
      </ScrollReveal>

      <ScrollReveal animation="fade-up" delay={120}>
        <Card>
        <CardHeader>
          <CardTitle>Manage checkpoints</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Add items once — they appear on every day&apos;s checklist automatically. Edit or delete here only when you want to change your routine.
          </p>

          <form onSubmit={handleAdd} className="flex flex-col gap-2 sm:flex-row">
            <Input
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="e.g. Workout 1, Protein goal, 10k steps"
              className="flex-1"
            />
            <Button type="submit" disabled={adding || !newTitle.trim()} className="w-full sm:w-auto shrink-0">
              <Plus className="h-4 w-4 mr-1" />
              {adding ? 'Adding...' : 'Add'}
            </Button>
          </form>

          {templates.length > 0 && (
            <ul className="space-y-2">
              {templates.map((checkpoint) => (
                <li
                  key={checkpoint.id}
                  className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2"
                >
                  {editingId === checkpoint.id ? (
                    <>
                      <Input
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        className="flex-1"
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') saveEdit(checkpoint.id)
                          if (e.key === 'Escape') cancelEdit()
                        }}
                      />
                      <Button
                        type="button"
                        size="sm"
                        onClick={() => saveEdit(checkpoint.id)}
                        disabled={savingEdit || !editTitle.trim()}
                      >
                        Save
                      </Button>
                      <Button type="button" size="sm" variant="ghost" onClick={cancelEdit}>
                        <X className="h-4 w-4" />
                      </Button>
                    </>
                  ) : (
                    <>
                      <span className="flex-1 text-sm font-medium">{checkpoint.title}</span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => startEdit(checkpoint)}
                        aria-label="Edit checkpoint"
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(checkpoint.id)}
                        disabled={deletingId === checkpoint.id}
                        aria-label="Delete checkpoint"
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
      </ScrollReveal>
    </div>
  )
}
