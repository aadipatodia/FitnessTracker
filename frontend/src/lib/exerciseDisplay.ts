/** Combo exercises like "2 box jump + 5 burpees" — one logged rep = one full round. */

const COMBO_LEADING_COUNT = /^\s*(\d+)/

export function isComboExercise(exerciseName: string | undefined | null): boolean {
  return Boolean(exerciseName?.includes('+'))
}

export function parseComboSegments(exerciseName: string): Array<[number, string]> {
  if (!isComboExercise(exerciseName)) return []

  const segments: Array<[number, string]> = []
  for (const part of exerciseName.split('+')) {
    const trimmed = part.trim()
    if (!trimmed) continue

    const match = COMBO_LEADING_COUNT.exec(trimmed)
    if (match) {
      const count = Number(match[1])
      const label = trimmed.slice(match[0].length).trim()
      if (label) segments.push([count, label])
    } else {
      segments.push([1, trimmed])
    }
  }
  return segments
}

function pluralizeMovement(total: number, label: string): string {
  if (total === 1 || label.endsWith('s')) return label
  return `${label}s`
}

export function formatComboTotals(exerciseName: string, rounds: number): string | null {
  if (rounds <= 0) return null
  const totals = parseComboSegments(exerciseName).map(
    ([count, label]) => [count * rounds, label] as [number, string],
  )
  if (!totals.length) return null
  return totals.map(([total, label]) => `${total} ${pluralizeMovement(total, label)}`).join(' + ')
}

export function repUnit(exerciseName: string | undefined | null): 'rounds' | 'reps' {
  return isComboExercise(exerciseName) ? 'rounds' : 'reps'
}

export function formatExerciseSet(
  exerciseName: string,
  set: { weight_kg?: number | null; reps?: number | null },
): string {
  const unit = repUnit(exerciseName)
  const reps = set.reps

  let base: string
  if (set.weight_kg) {
    base = `${set.weight_kg}kg × ${reps ?? '?'} ${unit}`
  } else {
    base = `${reps ?? '?'} ${unit}`
  }

  if (reps && isComboExercise(exerciseName)) {
    const totals = formatComboTotals(exerciseName, reps)
    if (totals) return `${base} (${totals})`
  }
  return base
}
