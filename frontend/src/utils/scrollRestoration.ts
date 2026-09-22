import type { NavigationType } from 'react-router-dom'

export type ScrollRestorationAction =
  | { kind: 'anchor'; hash: string }
  | { kind: 'restore'; top: number }
  | { kind: 'top' }

export function resolveScrollRestoration(
  navigationType: NavigationType,
  hash: string,
  savedTop: number | undefined,
): ScrollRestorationAction {
  if (hash) {
    return { kind: 'anchor', hash }
  }
  if (navigationType === 'POP') {
    return { kind: 'restore', top: savedTop ?? 0 }
  }
  return { kind: 'top' }
}

export function findAnchorElement(hash: string, root: ParentNode = document): HTMLElement | null {
  const rawId = hash.replace(/^#/, '')
  if (!rawId) return null

  const decodedId = decodeURIComponent(rawId)
  if (root instanceof Document) {
    const byId = root.getElementById(decodedId)
    if (byId) return byId
  }

  for (const element of root.querySelectorAll<HTMLElement>('[id], [name]')) {
    if (element.id === decodedId || element.getAttribute('name') === decodedId) {
      return element
    }
  }
  return null
}
