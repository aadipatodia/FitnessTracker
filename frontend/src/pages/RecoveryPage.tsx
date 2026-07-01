import { useEffect, useState } from 'react'
import { Trash2 } from 'lucide-react'
import { api, RecoveryLog } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input, Label } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDate, todayISO } from '@/lib/utils'

export function RecoveryPage() {
  const [logs, setLogs] = useState<RecoveryLog[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [logDate, setLogDate] = useState(todayISO())
  const [sleep, setSleep] = useState('')
  const [water, setWater] = useState('')
  const [deletingId, setDeletingId] = useState<number | null>(null)

  useEffect(() => {
    api.getRecoveryLogs().then(setLogs).catch(console.error).finally(() => setLoading(false))
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const log = await api.logRecovery({
        log_date: logDate,
        sleep_hours: sleep ? parseFloat(sleep) : undefined,
        water_liters: water ? parseFloat(water) : undefined,
      })
      setLogs([log, ...logs.filter(l => l.log_date !== log.log_date)])
      setSleep('')
      setWater('')
    } catch (err) {
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this recovery log?')) return
    setDeletingId(id)
    try {
      await api.deleteRecoveryLog(id)
      setLogs(logs.filter(l => l.id !== id))
    } catch (err) {
      console.error(err)
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Recovery</h1>
        <p className="text-muted-foreground">Track sleep and hydration</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Log recovery</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label>Date (wake-up date for sleep)</Label>
              <Input type="date" value={logDate} onChange={(e) => setLogDate(e.target.value)} />
              <p className="text-xs text-muted-foreground">
                Sleep is counted for the night before this date through this morning.
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Sleep (hours)</Label>
                <Input type="number" step="0.5" value={sleep} onChange={(e) => setSleep(e.target.value)} placeholder="7.5" />
              </div>
              <div className="space-y-2">
                <Label>Water (liters)</Label>
                <Input type="number" step="0.1" value={water} onChange={(e) => setWater(e.target.value)} placeholder="2.5" />
              </div>
            </div>
            <Button type="submit" disabled={saving}>{saving ? 'Saving...' : 'Save recovery log'}</Button>
          </form>
        </CardContent>
      </Card>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : (
        <div className="space-y-3">
          {logs.map((log) => (
            <Card key={log.id}>
              <CardContent className="py-4">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <span className="font-medium">{formatDate(log.log_date)}</span>
                  <div className="flex items-center gap-2 sm:gap-4">
                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
                      {log.sleep_hours != null && <span>😴 {log.sleep_hours}h sleep</span>}
                      {log.water_liters != null && <span>💧 {log.water_liters}L water</span>}
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(log.id)}
                      disabled={deletingId === log.id}
                      aria-label="Delete recovery log"
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
