export interface TrainingGoal {
  training_goal_id: number
  goal_code: string
  goal_name: string
  description: string | null
  default_sets: number
  default_reps: number
  default_rest_seconds: number
}

export interface BodyPart {
  body_part_id: number
  body_part_code: string
  name_en: string
  name_zh: string
  display_order: number
}

export interface Exercise {
  exercise_id: number
  exercise_name: string
  body_part: BodyPart
  difficulty_level: string
  equipment: string
  movement_type: string
  description: string
  is_active: boolean
}

export interface Profile {
  user_id: string
  name: string
  gender: string | null
  age: number
  height_cm: string
  training_experience: string
  training_goal: TrainingGoal
  training_days_per_week: number
  training_duration_minutes: number
  preferred_body_parts: BodyPart[]
  latest_weight_kg: string
  created_at: string
  updated_at: string
}

export interface PlanExercise {
  plan_exercise_id: number
  exercise_order: number
  target_sets: number
  target_reps: number
  rest_seconds: number
  notes: string | null
  exercise: Exercise
}

export interface PlanDay {
  plan_day_id: number
  day_number: number
  day_name: string
  focus_summary: string
  exercises: PlanExercise[]
}

export interface WorkoutPlan {
  plan_id: number
  plan_name: string
  training_goal: TrainingGoal
  training_days_per_week: number
  training_duration_minutes: number
  algorithm_version: string
  status: string
  generated_at: string
  days: PlanDay[]
}

export interface WorkoutSet {
  workout_set_id: number
  set_order: number
  set_number: number
  weight_kg: string
  reps: number
  is_warmup: boolean
  notes: string | null
  logged_at: string
  exercise: Exercise
}

export interface WorkoutSession {
  session_id: number
  session_name: string
  status: string
  started_at: string
  ended_at: string | null
  notes: string | null
  sets: WorkoutSet[]
}

export interface BodyRecord {
  body_record_id: number
  recorded_on: string
  weight_kg: string
  notes: string | null
  created_at: string
}

export interface MetricPoint {
  label: string
  value: number
}

export interface DashboardData {
  completed_workouts: number
  working_sets: number
  training_volume_kg: number
  latest_weight_kg: number | null
  weight_change_kg: number | null
  most_trained_body_part: string | null
  most_used_exercise: string | null
  weekly_volume: MetricPoint[]
  weight_history: MetricPoint[]
  recent_workouts: Array<{
    session_id: number
    session_name: string
    started_at: string
    set_count: number
    volume_kg: number
  }>
}
