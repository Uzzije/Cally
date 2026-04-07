type ErrorScreenProps = {
  title: string
  message: string
  onRetry: () => void
}

export function ErrorScreen({ title, message, onRetry }: ErrorScreenProps) {
  return (
    <main className="app-shell centered-shell">
      <section className="paper-panel status-panel">
        <p className="eyebrow">Session Error</p>
        <h1>{title}</h1>
        <p>{message}</p>
        <button className="primary-button button-md" onClick={onRetry}>
          Try Again
        </button>
      </section>
    </main>
  )
}
