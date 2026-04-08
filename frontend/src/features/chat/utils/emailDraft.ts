import type { EmailDraftBlock } from '../types'
import type { TempBlockedTimeEntry } from '../../settings/types'


function createTempBlockedTimeId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `temp-blocked-${crypto.randomUUID()}`
  }

  return `temp-blocked-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export function buildEmailDraftClipboardText(block: EmailDraftBlock) {
  const lines = [
    `To: ${block.to.join(', ')}`,
  ]

  if (block.cc && block.cc.length > 0) {
    lines.push(`Cc: ${block.cc.join(', ')}`)
  }

  lines.push(`Subject: ${block.subject}`)
  lines.push('')
  lines.push(block.body)

  return lines.join('\n')
}

export function hasSuggestedTimesInEmailDraft(block: Pick<EmailDraftBlock, 'suggested_times'>) {
  return Array.isArray(block.suggested_times) && block.suggested_times.length > 0
}

export function extractTempBlockedTimesFromEmailDraft(
  block: EmailDraftBlock,
  now: Date = new Date(),
): TempBlockedTimeEntry[] {
  return (block.suggested_times ?? []).map((suggestedTime) => ({
    id: createTempBlockedTimeId(),
    label: `Hold for ${block.subject}`,
    date: suggestedTime.date,
    start: suggestedTime.start,
    end: suggestedTime.end,
    timezone: suggestedTime.timezone,
    source: 'email_draft' as const,
    created_at: now.toISOString(),
  }))
}
