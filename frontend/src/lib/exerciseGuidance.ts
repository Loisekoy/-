import type { Exercise, PlanDay, PlanExercise } from '../api/types'

const FALLBACK_IMAGES: Record<string, string> = {
  chest: '/exercise-images/chest.svg',
  back: '/exercise-images/back.svg',
  shoulders: '/exercise-images/shoulders.svg',
  biceps: '/exercise-images/biceps.svg',
  triceps: '/exercise-images/triceps.svg',
  legs: '/exercise-images/legs.svg',
  glutes: '/exercise-images/glutes.svg',
  core: '/exercise-images/core.svg',
}

const BODY_PART_OBJECTIVES: Record<string, string> = {
  chest: '以推的動作刺激胸大肌，保持肩胛穩定，感受胸部出力。',
  back: '以拉的動作訓練背闊肌與中背，專注肩胛往後往下收。',
  shoulders: '建立肩部推舉與側平舉能力，避免聳肩代償。',
  biceps: '控制手肘位置，用二頭肌完成彎舉，不靠身體擺動。',
  triceps: '加強手臂伸直力量，讓手肘穩定並完整伸展。',
  legs: '以深蹲、腿推或髖膝伸展訓練下肢力量，保持膝蓋與腳尖同向。',
  glutes: '用臀部主導髖伸展，避免下背過度代償。',
  core: '建立軀幹穩定，維持腹壓與中立脊椎。',
}

const BODY_PART_CUES: Record<string, string[]> = {
  chest: ['肩胛微收並貼穩椅背或地面', '下放時控制速度，不要彈震', '推起時吐氣，手肘不要完全鎖死'],
  back: ['先讓肩胛往後往下，再用手肘帶動', '胸口保持打開，不要圓背', '回放時控制重量，感受背部被拉長'],
  shoulders: ['核心收緊，肋骨不要外翻', '動作路徑保持穩定，不要聳肩', '若肩膀夾痛，縮短活動範圍或降低重量'],
  biceps: ['手肘固定在身體兩側', '上舉與下放都要控制', '不要用腰或肩膀甩重量'],
  triceps: ['上臂盡量固定', '用手肘伸直完成動作', '頂端停 1 秒感受三頭肌收縮'],
  legs: ['腳掌踩穩，膝蓋跟腳尖方向一致', '下放時控制身體重心', '推起時不要讓膝蓋內夾'],
  glutes: ['先收核心再啟動臀部', '頂端夾臀但不要過度拱腰', '保持髖部穩定，不左右歪斜'],
  core: ['維持自然呼吸，不憋氣', '想像肚臍微微往內收', '腰椎保持中立，不塌腰'],
}

export function getExerciseImageSrc(exercise: Exercise): string {
  return (
    exercise.gif_url ??
    exercise.image_url ??
    FALLBACK_IMAGES[exercise.body_part.body_part_code] ??
    '/exercise-images/core.svg'
  )
}

export function getExerciseInstructions(exercise: Exercise): string[] {
  return exercise.instructions.length > 0 ? exercise.instructions : getExerciseCues(exercise)
}

export function getPrimaryMuscles(exercise: Exercise): string[] {
  return exercise.target_muscles.length > 0
    ? exercise.target_muscles
    : [exercise.body_part.name_en]
}

export function getExerciseObjective(exercise: Exercise): string {
  return BODY_PART_OBJECTIVES[exercise.body_part.body_part_code] ?? '以安全、穩定、可控制的節奏完成每一次動作。'
}

export function getExerciseCues(exercise: Exercise): string[] {
  return BODY_PART_CUES[exercise.body_part.body_part_code] ?? [
    '先用輕重量熟悉動作路徑',
    '每一下都保持穩定控制',
    '若出現疼痛請立即停止',
  ]
}

export function getIntensityTip(item: PlanExercise): string {
  const { difficulty_level: difficulty, movement_type: movement } = item.exercise
  if (difficulty === 'beginner') {
    return `建議用可以穩定完成 ${item.target_reps} 下、最後仍保留 2–3 下餘力的重量。`
  }
  if (movement === 'compound') {
    return `這是主要複合動作，可稍微挑戰重量，但每組都要保留 1–2 下餘力。`
  }
  return '這是輔助或孤立動作，重量不用太重，優先感受目標肌群收縮。'
}

export function getExerciseRole(item: PlanExercise, index: number): string {
  if (index === 0 && item.exercise.movement_type === 'compound') return '今日主要動作'
  if (item.exercise.movement_type === 'compound') return '複合訓練'
  return '輔助訓練'
}

export function getDayObjective(day: PlanDay): string {
  const focus = day.focus_summary.replaceAll('＋', '、')
  const mainExercise = day.exercises.find((item) => item.exercise.movement_type === 'compound') ?? day.exercises[0]
  return `今天主要訓練 ${focus}。先完成 ${mainExercise.exercise.exercise_name} 這類主要動作，再接續輔助動作補足訓練量。`
}
