import { Dumbbell } from 'lucide-react'

export function Brand() {
  return (
    <span className="brand" aria-label="Fitness Tracking Management System">
      <span className="brand__mark" aria-hidden="true">
        <Dumbbell size={24} strokeWidth={2.2} />
      </span>
      <span className="brand__full">Fitness Tracking Management System</span>
      <span className="brand__compact">Fitness Tracker</span>
    </span>
  )
}
