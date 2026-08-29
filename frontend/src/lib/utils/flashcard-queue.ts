import { FlashcardItem } from '@/lib/types/study'

export function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

export function isDue(item: FlashcardItem, today: string): boolean {
  return !item.due || item.due <= today
}

/** Due cards first (in their original order), then upcoming cards soonest-due
 * first. Retrieval practice works best distributed over time (Dunlosky et al.
 * 2013) - surfacing what's actually due, instead of always starting at card
 * 1, is what makes that spacing effect show up in practice.
 *
 * Shared by FlashcardViewer (quick/self-graded mode) and
 * GuidedFlashcardSession (AI-graded mode) so both modes agree on ordering. */
export function buildQueue(items: FlashcardItem[]): number[] {
  const today = todayIso()
  const due: number[] = []
  const upcoming: number[] = []
  items.forEach((item, index) => {
    if (isDue(item, today)) {
      due.push(index)
    } else {
      upcoming.push(index)
    }
  })
  upcoming.sort((a, b) => (items[a].due ?? '') < (items[b].due ?? '') ? -1 : 1)
  return [...due, ...upcoming]
}

/** Just the due cards, in original order - the queue a guided session works
 * through (a session's job is to clear what's due, not to page through
 * upcoming cards too). */
export function buildDueQueue(items: FlashcardItem[]): number[] {
  const today = todayIso()
  const due: number[] = []
  items.forEach((item, index) => {
    if (isDue(item, today)) {
      due.push(index)
    }
  })
  return due
}
