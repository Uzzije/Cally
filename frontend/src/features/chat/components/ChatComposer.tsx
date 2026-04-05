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
      />
      <button
        className="primary-button button-md"
        disabled={disabled || value.trim().length === 0}
        onClick={onSubmit}
      >
        {disabled ? 'Thinking…' : 'Send'}
      </button>
    </div>
  )
}

