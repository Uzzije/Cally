import type { KeyboardEvent } from 'react'

export function ChatComposer({
  value,
  disabled,
  onChange,
  onSubmit,
}: {
  value: string
  disabled: boolean
  onChange: (value: string) => void
  onSubmit: () => void
}) {
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== 'Enter' || event.shiftKey) {
      return
    }

    event.preventDefault()
    if (disabled || value.trim().length === 0) {
      return
    }

    onSubmit()
  }

  return (
    <div className="chat-composer">
      <textarea
        aria-label="Chat message"
        className="chat-composer-input"
        disabled={disabled}
        placeholder="Ask about your calendar…"
        rows={3}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
      />
      <button
        className="primary-button button-md"
        disabled={disabled || value.trim().length === 0}
        type="button"
        onClick={onSubmit}
      >
        {disabled ? 'Thinking…' : 'Send'}
      </button>
    </div>
  )
}
