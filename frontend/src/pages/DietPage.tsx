import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AlertTriangle, Camera, Plus, Sparkles, Trash2, Upload, X } from 'lucide-react'
import { api, DietLog, MealPhotoAnalysis } from '@/lib/api'
import { PageHeader } from '@/components/PageHeader'
import { Button } from '@/components/ui/button'
import { ScrollReveal, revealDelay } from '@/components/ScrollReveal'
import { Input, Label, Select, Textarea } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDate, todayISO } from '@/lib/utils'

function formatMacros(p: number, c: number, f: number, fi: number) {
  return `P:${Math.round(p)}g · C:${Math.round(c)}g · F:${Math.round(f)}g · Fi:${Math.round(fi)}g`
}

// Entries saved from the photo-review flow store the full portion description in `unit`
// (with quantity fixed at 1) rather than the count+unit split used by text logging.
const PHOTO_FLOW_SOURCES = new Set(['gemini_photo', 'manual'])

interface ReviewItem {
  key: string
  name: string
  quantity: string
  calories: string
  protein_g: string
  carbs_g: string
  fat_g: string
  isManual: boolean
}

function toReviewItem(item: { name: string; estimated_quantity: string; calories: number; protein_g: number; carbs_g: number; fat_g: number }, isManual: boolean): ReviewItem {
  return {
    key: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    name: item.name,
    quantity: item.estimated_quantity,
    calories: String(Math.round(item.calories)),
    protein_g: String(Math.round(item.protein_g)),
    carbs_g: String(Math.round(item.carbs_g)),
    fat_g: String(Math.round(item.fat_g)),
    isManual,
  }
}

function num(value: string): number {
  const n = Number(value)
  return Number.isFinite(n) ? n : 0
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

  const cameraInputRef = useRef<HTMLInputElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState<string | null>(null)
  const [analyzingPhoto, setAnalyzingPhoto] = useState(false)
  const [photoError, setPhotoError] = useState<string | null>(null)
  const [review, setReview] = useState<{ confidence: MealPhotoAnalysis['confidence']; items: ReviewItem[] } | null>(null)
  const [savingPhoto, setSavingPhoto] = useState(false)

  useEffect(() => {
    return () => {
      if (photoPreviewUrl) URL.revokeObjectURL(photoPreviewUrl)
    }
  }, [photoPreviewUrl])

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

  const handlePhotoSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return

    if (photoPreviewUrl) URL.revokeObjectURL(photoPreviewUrl)
    setPhotoError(null)
    setReview(null)
    setPhotoPreviewUrl(URL.createObjectURL(file))
    setAnalyzingPhoto(true)
    try {
      const result = await api.analyzeMealPhoto(file)
      setReview({
        confidence: result.confidence,
        items: result.items.map((item) => toReviewItem(item, false)),
      })
    } catch (err) {
      setPhotoError(err instanceof Error ? err.message : 'Could not analyze this photo')
    } finally {
      setAnalyzingPhoto(false)
    }
  }

  const updateReviewItem = (key: string, field: keyof ReviewItem, value: string) => {
    setReview((prev) => prev && {
      ...prev,
      items: prev.items.map((item) => item.key === key ? { ...item, [field]: value } : item),
    })
  }

  const removeReviewItem = (key: string) => {
    setReview((prev) => prev && { ...prev, items: prev.items.filter((item) => item.key !== key) })
  }

  const addManualItem = () => {
    setReview((prev) => {
      const blank = toReviewItem({ name: '', estimated_quantity: '', calories: 0, protein_g: 0, carbs_g: 0, fat_g: 0 }, true)
      if (!prev) return { confidence: 'medium', items: [blank] }
      return { ...prev, items: [...prev.items, blank] }
    })
  }

  const cancelReview = () => {
    if (photoPreviewUrl) URL.revokeObjectURL(photoPreviewUrl)
    setPhotoPreviewUrl(null)
    setReview(null)
    setPhotoError(null)
  }

  const reviewTotals = useMemo(() => {
    if (!review) return { calories: 0, protein: 0, carbs: 0, fat: 0 }
    return review.items.reduce(
      (acc, item) => ({
        calories: acc.calories + num(item.calories),
        protein: acc.protein + num(item.protein_g),
        carbs: acc.carbs + num(item.carbs_g),
        fat: acc.fat + num(item.fat_g),
      }),
      { calories: 0, protein: 0, carbs: 0, fat: 0 }
    )
  }, [review])

  const handleConfirmSave = async () => {
    if (!review || review.items.length === 0) return
    setSavingPhoto(true)
    setPhotoError(null)
    try {
      const log = await api.logDietEntries({
        log_date: logDate,
        meal_type: mealType,
        entries: review.items.map((item) => ({
          food_name: item.name.trim() || 'Food item',
          quantity: 1,
          unit: item.quantity.trim() || 'serving',
          calories: num(item.calories),
          protein_g: num(item.protein_g),
          carbs_g: num(item.carbs_g),
          fat_g: num(item.fat_g),
          fibre_g: 0,
          source: item.isManual ? 'manual' : 'gemini_photo',
        })),
      })
      if (log.log_date === viewDate) {
        setLogs([log, ...logs.filter(l => l.id !== log.id)])
      } else {
        await loadLogs(viewDate)
      }
      cancelReview()
    } catch (err) {
      setPhotoError(err instanceof Error ? err.message : 'Could not save this meal')
    } finally {
      setSavingPhoto(false)
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
            <CardTitle className="flex items-center justify-center gap-2 sm:justify-start">
              <Camera className="h-4 w-4 text-primary" />
              Snap a meal
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <input
              ref={cameraInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              onChange={handlePhotoSelected}
            />
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handlePhotoSelected}
            />

            {!review && !analyzingPhoto && (
              <div className="flex flex-wrap justify-center gap-3 sm:justify-start">
                <Button type="button" onClick={() => cameraInputRef.current?.click()}>
                  <Camera className="h-4 w-4" />
                  Snap a meal
                </Button>
                <Button type="button" variant="outline" onClick={() => fileInputRef.current?.click()}>
                  <Upload className="h-4 w-4" />
                  Upload photo
                </Button>
              </div>
            )}

            {photoError && !review && (
              <p className="text-sm text-destructive">{photoError}</p>
            )}

            {analyzingPhoto && (
              <div className="space-y-3">
                {photoPreviewUrl && (
                  <img src={photoPreviewUrl} alt="Uploaded meal" className="max-h-64 w-full rounded-xl object-cover" />
                )}
                <div className="flex items-center justify-center gap-3 py-4">
                  <div className="luxury-spinner" />
                  <span className="text-meta">FitAI is analyzing your photo...</span>
                </div>
              </div>
            )}

            {review && !analyzingPhoto && (
              <div className="space-y-4">
                {photoPreviewUrl && (
                  <img src={photoPreviewUrl} alt="Uploaded meal" className="max-h-64 w-full rounded-xl object-cover" />
                )}

                {review.confidence === 'low' && (
                  <div className="flex items-start gap-2 rounded-lg border border-primary/30 bg-primary/10 p-3 text-sm text-primary">
                    <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                    <span>FitAI wasn't very confident about this estimate — double-check the items and macros below before saving.</span>
                  </div>
                )}

                {photoError && (
                  <p className="text-sm text-destructive">{photoError}</p>
                )}

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

                <div className="space-y-3">
                  {review.items.map((item) => (
                    <div key={item.key} className="space-y-2 rounded-lg border border-border/60 bg-muted/30 p-3">
                      <div className="flex items-center gap-2">
                        <Input
                          value={item.name}
                          onChange={(e) => updateReviewItem(item.key, 'name', e.target.value)}
                          placeholder="Food name"
                          className="flex-1"
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removeReviewItem(item.key)}
                          aria-label="Remove item"
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
                        <div className="space-y-1">
                          <Label className="text-xs">Quantity</Label>
                          <Input
                            value={item.quantity}
                            onChange={(e) => updateReviewItem(item.key, 'quantity', e.target.value)}
                            placeholder="e.g. 2 rotis"
                          />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Calories</Label>
                          <Input
                            type="number"
                            value={item.calories}
                            onChange={(e) => updateReviewItem(item.key, 'calories', e.target.value)}
                          />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Protein (g)</Label>
                          <Input
                            type="number"
                            value={item.protein_g}
                            onChange={(e) => updateReviewItem(item.key, 'protein_g', e.target.value)}
                          />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Carbs (g)</Label>
                          <Input
                            type="number"
                            value={item.carbs_g}
                            onChange={(e) => updateReviewItem(item.key, 'carbs_g', e.target.value)}
                          />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs">Fat (g)</Label>
                          <Input
                            type="number"
                            value={item.fat_g}
                            onChange={(e) => updateReviewItem(item.key, 'fat_g', e.target.value)}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                <Button type="button" variant="secondary" size="sm" onClick={addManualItem}>
                  <Plus className="h-4 w-4" />
                  Add item
                </Button>

                <div className="flex flex-col gap-1 border-t border-border pt-3 text-base sm:flex-row sm:justify-between">
                  <span className="text-label normal-case">Total</span>
                  <span className="font-semibold text-foreground">
                    {Math.round(reviewTotals.calories)} kcal · {formatMacros(reviewTotals.protein, reviewTotals.carbs, reviewTotals.fat, 0)}
                  </span>
                </div>

                <div className="flex flex-wrap gap-3">
                  <Button
                    type="button"
                    onClick={handleConfirmSave}
                    disabled={savingPhoto || review.items.length === 0}
                  >
                    {savingPhoto ? 'Saving...' : 'Confirm & Save'}
                  </Button>
                  <Button type="button" variant="outline" onClick={cancelReview} disabled={savingPhoto}>
                    <X className="h-4 w-4" />
                    Cancel
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </ScrollReveal>

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
                          {PHOTO_FLOW_SOURCES.has(entry.source) ? entry.unit : `${entry.quantity} ${entry.unit}`}
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
