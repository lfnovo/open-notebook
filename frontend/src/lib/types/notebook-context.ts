/** Chat-context inclusion mode for a notebook source or note. */
export type ContextMode = 'off' | 'insights' | 'full'
export type NoteContextMode = Exclude<ContextMode, 'insights'>

export interface ContextSelections {
  sources: Record<string, ContextMode>
  notes: Record<string, NoteContextMode>
}
