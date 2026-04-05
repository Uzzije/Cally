import { describe, expect, it } from 'vitest'

import { parseLocationLink, toDisplayText } from './eventContent'

describe('event content formatting', () => {
  it('converts html event descriptions into readable text', () => {
    const html = '<div>Hi&nbsp;Uzoma!</div><div><strong>Wednesday</strong><br/>10:00am</div>'

    const output = toDisplayText(html)

    expect(output).toContain('Hi Uzoma!')
    expect(output).toContain('Wednesday')
    expect(output).toContain('10:00am')
    expect(output).not.toContain('<div>')
    expect(output).not.toContain('&nbsp;')
  })

  it('returns a link model for valid web locations', () => {
    const location = parseLocationLink('https://ramp.zoom.us/j/83590217233?pwd=secret')

    expect(location.href).toBe('https://ramp.zoom.us/j/83590217233?pwd=secret')
    expect(location.text).toBe('ramp.zoom.us/j/83590217233')
  })

  it('returns plain text when location is not a url', () => {
    const location = parseLocationLink('Conference Room A')

    expect(location.href).toBeNull()
    expect(location.text).toBe('Conference Room A')
  })
})
