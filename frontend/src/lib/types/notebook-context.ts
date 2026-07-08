/**
 * Chat-context inclusion mode for a notebook source or note.
 * - `auto`     → smart retrieval: relevant passages are vector-searched per
 *                message (the default for sources; keeps large libraries bounded)
 * - `insights` → legacy: inject the source's insights/summary verbatim
 * - `full`     → inject the full text verbatim (pin a critical source)
 * - `off`      → excluded from chat context
 */
export type ContextMode = 'off' | 'auto' | 'insights' | 'full'
export type NoteContextMode = Exclude<ContextMode, 'insights' | 'auto'>

export interface ContextSelections {
  sources: Record<string, ContextMode>
  notes: Record<string, NoteContextMode>
}
