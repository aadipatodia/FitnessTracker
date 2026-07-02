const API_BASE = '/api'

class ApiClient {
  private token: string | null = null

  setToken(token: string | null) {
    this.token = token
    if (token) localStorage.setItem('fitai_token', token)
    else localStorage.removeItem('fitai_token')
  }

  getToken(): string | null {
    if (!this.token) this.token = localStorage.getItem('fitai_token')
    return this.token
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    }
    const token = this.getToken()
    if (token) headers['Authorization'] = `Bearer ${token}`

    const res = await fetch(`${API_BASE}${path}`, { ...options, headers })

    if (res.status === 204) {
      return undefined as T
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Request failed' }))
      const message =
        typeof err.detail === 'string'
          ? err.detail
          : Array.isArray(err.detail)
            ? err.detail.map((e: { msg?: string }) => e.msg).filter(Boolean).join(', ') || 'Request failed'
            : 'Request failed'

      if (res.status === 401 && !path.startsWith('/auth/')) {
        this.setToken(null)
        window.location.href = '/login'
      }

      throw new Error(message)
    }

    return res.json()
  }

  // Auth
  register(data: { email: string; password: string; full_name: string }) {
    return this.request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  login(data: { email: string; password: string }) {
    return this.request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  getMe() {
    return this.request<User>('/auth/me')
  }

  requestPasswordReset(email: string) {
    return this.request<PasswordResetRequestResponse>('/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
    })
  }

  resetPassword(data: { email: string; reset_token: string; new_password: string }) {
    return this.request<{ message: string }>('/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  // Goals
  createGoal(data: GoalCreate) {
    return this.request<Goal>('/goals', { method: 'POST', body: JSON.stringify(data) })
  }

  getGoalGuidance(data: GoalGuidanceRequest) {
    return this.request<GoalGuidance>('/goals/guidance', { method: 'POST', body: JSON.stringify(data) })
  }

  evaluateGoal(data: GoalEvaluateRequest) {
    return this.request<GoalFeasibility>('/goals/evaluate', { method: 'POST', body: JSON.stringify(data) })
  }

  getActiveGoal() {
    return this.request<Goal | null>('/goals/active')
  }

  // Workouts
  createWorkout(data: WorkoutCreate) {
    return this.request<Workout>('/workouts', { method: 'POST', body: JSON.stringify(data) })
  }

  getWorkouts(params?: { workoutDate?: string; limit?: number }) {
    const search = new URLSearchParams()
    if (params?.workoutDate) search.set('workout_date', params.workoutDate)
    if (params?.limit) search.set('limit', String(params.limit))
    const query = search.toString()
    return this.request<Workout[]>(`/workouts${query ? `?${query}` : ''}`)
  }

  deleteWorkout(id: number) {
    return this.request<void>(`/workouts/${id}`, { method: 'DELETE' })
  }

  // Diet
  logDiet(data: DietLogCreate) {
    return this.request<DietLog>('/diet/log', { method: 'POST', body: JSON.stringify(data) })
  }

  getDietLogs(params?: { logDate?: string; limit?: number }) {
    const search = new URLSearchParams()
    if (params?.logDate) search.set('log_date', params.logDate)
    if (params?.limit) search.set('limit', String(params.limit))
    const query = search.toString()
    return this.request<DietLog[]>(`/diet/logs${query ? `?${query}` : ''}`)
  }

  deleteDietLog(id: number) {
    return this.request<void>(`/diet/logs/${id}`, { method: 'DELETE' })
  }

  // Body
  createBodyMetric(data: BodyMetricCreate) {
    return this.request<BodyMetric>('/body/metrics', { method: 'POST', body: JSON.stringify(data) })
  }

  getBodyMetrics() {
    return this.request<BodyMetric[]>('/body/metrics')
  }

  deleteBodyMetric(id: number) {
    return this.request<void>(`/body/metrics/${id}`, { method: 'DELETE' })
  }

  // Recovery
  logRecovery(data: RecoveryLogCreate) {
    return this.request<RecoveryLog>('/recovery/log', { method: 'POST', body: JSON.stringify(data) })
  }

  getRecoveryLogs() {
    return this.request<RecoveryLog[]>('/recovery/logs')
  }

  deleteRecoveryLog(id: number) {
    return this.request<void>(`/recovery/logs/${id}`, { method: 'DELETE' })
  }

  // Activities (cardio + daily movement)
  createActivity(data: ActivityLogCreate) {
    return this.request<ActivityLog>('/activities', { method: 'POST', body: JSON.stringify(data) })
  }

  getActivities(params?: { category?: string; logDate?: string; limit?: number }) {
    const search = new URLSearchParams()
    if (params?.category) search.set('category', params.category)
    if (params?.logDate) search.set('log_date', params.logDate)
    if (params?.limit) search.set('limit', String(params.limit))
    const query = search.toString()
    return this.request<ActivityLog[]>(`/activities${query ? `?${query}` : ''}`)
  }

  deleteActivity(id: number) {
    return this.request<void>(`/activities/${id}`, { method: 'DELETE' })
  }

  // Coach
  getDashboard() {
    return this.request<DashboardStats>('/coach/dashboard')
  }

  getCharts(days = 30) {
    return this.request<DashboardCharts>(`/coach/charts?days=${days}`)
  }

  analyze(type: 'daily' | 'weekly' | 'goal' = 'daily', analysisDate?: string) {
    return this.request<CoachingInsight[]>('/coach/analyze', {
      method: 'POST',
      body: JSON.stringify({
        analysis_type: type,
        analysis_date: analysisDate,
      }),
    })
  }

  getInsights(params?: { analysisDate?: string; analysisType?: string }) {
    const search = new URLSearchParams()
    if (params?.analysisDate) search.set('analysis_date', params.analysisDate)
    if (params?.analysisType) search.set('analysis_type', params.analysisType)
    const query = search.toString()
    return this.request<CoachingInsight[]>(`/coach/insights${query ? `?${query}` : ''}`)
  }

  // Checkpoints
  getCheckpoints() {
    return this.request<Checkpoint[]>('/checkpoints')
  }

  createCheckpoint(data: CheckpointCreate) {
    return this.request<Checkpoint>('/checkpoints', { method: 'POST', body: JSON.stringify(data) })
  }

  updateCheckpoint(id: number, data: CheckpointUpdate) {
    return this.request<Checkpoint>(`/checkpoints/${id}`, { method: 'PUT', body: JSON.stringify(data) })
  }

  deleteCheckpoint(id: number) {
    return this.request<void>(`/checkpoints/${id}`, { method: 'DELETE' })
  }

  getDailyCheckpoints(logDate: string) {
    return this.request<DailyCheckpoints>(`/checkpoints/daily?log_date=${logDate}`)
  }

  toggleCheckpoint(data: CheckpointToggle) {
    return this.request<DailyCheckpointItem>('/checkpoints/daily/toggle', {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }
}

export const api = new ApiClient()

// Types
export interface User {
  id: number
  email: string
  full_name: string
  gender?: string
  age?: number
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface PasswordResetRequestResponse {
  message: string
  reset_token?: string
}

export interface Goal {
  id: number
  goal_type: string
  title: string
  description?: string
  target_body_fat?: number
  current_body_fat?: number
  target_weight?: number
  current_weight?: number
  target_exercise?: string
  target_weight_lifted?: number
  target_calories?: number
  target_protein?: number
  is_active: boolean
  created_at: string
  target_date?: string
}

export interface GoalCreate {
  goal_type: string
  title: string
  description?: string
  gender?: string
  age?: number
  target_body_fat?: number
  current_body_fat?: number
  target_weight?: number
  current_weight?: number
  target_exercise?: string
  target_weight_lifted?: number
  target_calories?: number
  target_protein?: number
  target_date?: string
}

export interface GoalGuidanceRequest {
  goal_type: string
  end_goal?: string
  gender?: string
  age?: number
}

export interface GoalGuidance {
  title: string
  tips: string[]
}

export interface GoalEvaluateRequest {
  goal_type: string
  end_goal?: string
  gender?: string
  age?: number
  target_date?: string
  current_body_fat?: number
  target_body_fat?: number
  current_weight?: number
  target_weight?: number
  target_exercise?: string
  current_weight_lifted?: number
  target_weight_lifted?: number
}

export interface GoalFeasibility {
  realistic: boolean
  intensity: string
  weeks_available: number
  headline: string
  expected_by_deadline: string
  aggressive_plan: string
  projected_body_fat?: number
  projected_weight?: number
  projected_lift?: number
  target_calories?: number
  target_protein?: number
}

export interface SetCreate {
  set_number: number
  weight_kg?: number
  reps?: number
  time_seconds?: number
  rest_seconds?: number
}

export interface ExerciseCreate {
  exercise_name: string
  order_index?: number
  notes?: string
  sets: SetCreate[]
}

export interface WorkoutCreate {
  workout_date: string
  name?: string
  notes?: string
  duration_minutes?: number
  exercises: ExerciseCreate[]
}

export interface Workout {
  id: number
  workout_date: string
  name?: string
  notes?: string
  duration_minutes?: number
  calories_burned?: number
  created_at: string
  exercises: {
    id: number
    exercise_name: string
    order_index: number
    notes?: string
    sets: {
      id: number
      set_number: number
      weight_kg?: number
      reps?: number
      time_seconds?: number
      rest_seconds?: number
    }[]
  }[]
}

export interface DietLogCreate {
  log_date: string
  meal_type?: string
  food_input: string
}

export interface DietLog {
  id: number
  log_date: string
  meal_type?: string
  created_at: string
  entries: {
    id: number
    raw_input: string
    food_name: string
    quantity: number
    unit: string
    calories: number
    protein_g: number
    carbs_g: number
    fat_g: number
    fibre_g: number
    source: string
  }[]
  total_calories: number
  total_protein: number
  total_carbs: number
  total_fat: number
  total_fibre: number
}

export interface BodyMetricCreate {
  recorded_date: string
  weight_kg?: number
  body_fat_percent?: number
  waist_cm?: number
  notes?: string
}

export interface BodyMetric {
  id: number
  recorded_date: string
  weight_kg?: number
  body_fat_percent?: number
  waist_cm?: number
  photo_url?: string
  notes?: string
  created_at: string
}

export interface RecoveryLogCreate {
  log_date: string
  sleep_hours?: number
  water_liters?: number
  steps?: number
}

export interface RecoveryLog {
  id: number
  log_date: string
  sleep_hours?: number
  water_liters?: number
  steps?: number
  created_at: string
}

export interface ActivityLogCreate {
  log_date: string
  activity_name: string
  duration_minutes: number
  category: 'cardio'
}

export interface ActivityLog {
  id: number
  log_date: string
  activity_name: string
  duration_minutes: number
  category: string
  calories_burned: number
  created_at: string
}

export interface DashboardStats {
  current_weight?: number
  current_body_fat?: number
  goal_progress_percent: number
  calories_today: number
  calories_burned_today: number
  calories_burned_workouts?: number
  calories_burned_cardio?: number
  calories_burned_everyday?: number
  protein_today: number
  recovery_score: number
  workout_streak: number
  target_calories?: number
  target_protein?: number
  active_goal?: Goal
}

export interface ChartDataPoint {
  date: string
  value: number
  label?: string
}

export interface DashboardCharts {
  weight_trend: ChartDataPoint[]
  body_fat_trend: ChartDataPoint[]
  strength_progression: { date: string; exercise: string; max_weight: number }[]
  protein_intake: ChartDataPoint[]
  calories_intake: ChartDataPoint[]
}

export interface CoachingInsight {
  id: number
  insight_type: string
  title: string
  content: string
  metadata_json?: Record<string, unknown>
  created_at: string
}

export interface Checkpoint {
  id: number
  title: string
  sort_order: number
  created_at: string
}

export interface CheckpointCreate {
  title: string
}

export interface CheckpointUpdate {
  title?: string
  sort_order?: number
}

export interface DailyCheckpointItem {
  id: number
  title: string
  sort_order: number
  completed: boolean
  completed_at?: string
}

export interface DailyCheckpoints {
  log_date: string
  items: DailyCheckpointItem[]
  total: number
  completed_count: number
}

export interface CheckpointToggle {
  checkpoint_id: number
  log_date: string
  completed: boolean
}
