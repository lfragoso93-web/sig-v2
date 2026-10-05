import { describe, expect, it } from 'vitest'
import { findAnchorElement, resolveScrollRestoration } from './scrollRestoration'

describe('scrollRestoration', () => {
  it('scrolls new pathname navigations to the top', () => {
    expect(resolveScrollRestoration('PUSH', '', undefined)).toEqual({ kind: 'top' })
    expect(resolveScrollRestoration('REPLACE', '', 320)).toEqual({ kind: 'top' })
  })

  it('restores saved position on back and forward navigation', () => {
    expect(resolveScrollRestoration('POP', '', 480)).toEqual({ kind: 'restore', top: 480 })
    expect(resolveScrollRestoration('POP', '', undefined)).toEqual({ kind: 'restore', top: 0 })
  })

  it('keeps anchors in charge when a hash is present', () => {
    expect(resolveScrollRestoration('PUSH', '#target', 480)).toEqual({ kind: 'anchor', hash: '#target' })
    expect(resolveScrollRestoration('POP', '#target', 480)).toEqual({ kind: 'anchor', hash: '#target' })
  })

  it('finds anchors scoped to the scroll container', () => {
    const root = document.createElement('main')
    const target = document.createElement('section')
    target.id = 'target'
    root.appendChild(target)

    expect(findAnchorElement('#target', root)).toBe(target)
  })

  it('falls back to named anchors', () => {
    const root = document.createElement('main')
    const target = document.createElement('a')
    target.setAttribute('name', 'legacy-target')
    root.appendChild(target)

    expect(findAnchorElement('#legacy-target', root)).toBe(target)
  })
})
