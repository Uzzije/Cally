export function ChatStatusLine({
  text,
  tone = 'muted',
}: {
  text: string | null
  tone?: 'muted' | 'error'
}) {
  if (!text) {
    return null
  }

  return (
    <p className={`chat-status-line${tone === 'error' ? ' is-error' : ''}`}>
      {text}
    </p>
  )
}

