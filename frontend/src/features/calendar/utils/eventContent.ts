function normalizeWhitespace(value: string) {
  return value
    .replace(/\u00a0/g, ' ')
    .replace(/\r/g, '')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n[ \t]+/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/[ \t]{2,}/g, ' ')
    .trim()
}

function removeHtmlTagsWithFallback(value: string) {
  return normalizeWhitespace(value.replace(/<[^>]*>/g, ' '))
}

export function toDisplayText(value: string | null | undefined) {
  if (!value) {
    return ''
  }

  const trimmed = value.trim()
  const looksLikeHtml = /<\/?[a-z][\s\S]*>/i.test(trimmed)

  if (!looksLikeHtml) {
    return normalizeWhitespace(trimmed)
  }

  const htmlWithLineHints = trimmed
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/(div|p|li|tr|h[1-6])>/gi, '\n')

  if (typeof DOMParser === 'undefined') {
    return removeHtmlTagsWithFallback(htmlWithLineHints)
  }

  const parsed = new DOMParser().parseFromString(htmlWithLineHints, 'text/html')
  return normalizeWhitespace(parsed.body.textContent ?? '')
}

function buildUrlLabel(url: URL) {
  const path = url.pathname === '/' ? '' : url.pathname
  const label = `${url.hostname}${path}`

  if (label.length <= 56) {
    return label
  }

  return `${label.slice(0, 53)}...`
}

export function parseLocationLink(location: string | null | undefined) {
  const text = toDisplayText(location)

  if (!text) {
    return { text: 'Not provided', href: null as string | null }
  }

  try {
    const url = new URL(text)
    if (url.protocol === 'http:' || url.protocol === 'https:') {
      return { text: buildUrlLabel(url), href: url.toString() }
    }
  } catch {
    return { text, href: null as string | null }
  }

  return { text, href: null as string | null }
}
