export function LoadingScreen({ label }: { label: string }) {
  return (
    <main className="loading-screen" aria-live="polite">
      <span className="loading-screen__bar" aria-hidden="true" />
      <p>{label}</p>
    </main>
  )
}
