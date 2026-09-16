import { AlertCircle } from 'lucide-react'

export function ErrorNotice({ message }: { message: string }) {
  return (
    <div className="error-notice" role="alert">
      <AlertCircle size={19} aria-hidden="true" />
      <span>{message}</span>
    </div>
  )
}
