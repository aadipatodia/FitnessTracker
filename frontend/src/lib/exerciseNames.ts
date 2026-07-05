import type { ExerciseAssessment } from '@/lib/api'

const FUZZY_MATCH_THRESHOLD = 0.88

export function normalizeExerciseKey(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/[-_]/g, ' ')
    .replace(/[^\w\s]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function exerciseSimilarity(a: string, b: string): number {
  const left = normalizeExerciseKey(a)
  const right = normalizeExerciseKey(b)
  if (!left || !right) return 0
  if (left === right) return 1

  const maxLen = Math.max(left.length, right.length)
  if (maxLen === 0) return 1

  const matrix = Array.from({ length: left.length + 1 }, () =>
    Array<number>(right.length + 1).fill(0),
  )
  for (let i = 0; i <= left.length; i += 1) matrix[i][0] = i
  for (let j = 0; j <= right.length; j += 1) matrix[0][j] = j

  for (let i = 1; i <= left.length; i += 1) {
    for (let j = 1; j <= right.length; j += 1) {
      const cost = left[i - 1] === right[j - 1] ? 0 : 1
      matrix[i][j] = Math.min(
        matrix[i - 1][j] + 1,
        matrix[i][j - 1] + 1,
        matrix[i - 1][j - 1] + cost,
      )
    }
  }

  const distance = matrix[left.length][right.length]
  return 1 - distance / maxLen
}

export function findAssessmentForExercise(
  exerciseName: string,
  assessments: ExerciseAssessment[],
  usedKeys: Set<string> = new Set(),
): ExerciseAssessment | undefined {
  const chartKey = normalizeExerciseKey(exerciseName)

  for (const assessment of assessments) {
    const assessmentKey = assessment.exercise_key || normalizeExerciseKey(assessment.exercise)
    if (usedKeys.has(assessmentKey)) continue
    if (assessmentKey === chartKey) {
      usedKeys.add(assessmentKey)
      return assessment
    }
  }

  let best: ExerciseAssessment | undefined
  let bestScore = FUZZY_MATCH_THRESHOLD
  for (const assessment of assessments) {
    const assessmentKey = assessment.exercise_key || normalizeExerciseKey(assessment.exercise)
    if (usedKeys.has(assessmentKey)) continue
    const score = exerciseSimilarity(exerciseName, assessment.exercise)
    if (score >= bestScore) {
      bestScore = score
      best = assessment
    }
  }
  if (best) {
    usedKeys.add(best.exercise_key || normalizeExerciseKey(best.exercise))
  }
  return best
}

export function buildAssessmentLookup(
  assessments: ExerciseAssessment[],
): Record<string, ExerciseAssessment> {
  const lookup: Record<string, ExerciseAssessment> = {}
  const usedKeys = new Set<string>()
  for (const assessment of assessments) {
    const key = assessment.exercise_key || normalizeExerciseKey(assessment.exercise)
    if (usedKeys.has(key)) continue
    usedKeys.add(key)
    lookup[key] = assessment
  }
  return lookup
}
