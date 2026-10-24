import { create } from 'zustand'
import { persist } from 'zustand/middleware'

import {
  DEFAULT_ARTIFACT_VARIANT,
  sanitizeVariant,
  type ArtifactKind,
  type ArtifactVariant,
} from '@/lib/types/artifacts'

const KINDS: readonly ArtifactKind[] = ['report', 'deck']

/**
 * Coerce anything that came from the user or from storage to a valid kind.
 *
 * A persisted value outlives the code that wrote it, so it is never trusted:
 * if the set of valid kinds ever changes, an old entry must not reach the
 * Select, where it would render as an empty option.
 */
function sanitizeKind(kind: unknown): ArtifactKind {
  return KINDS.includes(kind as ArtifactKind) ? (kind as ArtifactKind) : 'report'
}

interface ArtifactFormState {
  kind: ArtifactKind
  variant: ArtifactVariant
  setKind: (kind: ArtifactKind) => void
  setVariant: (variant: ArtifactVariant) => void
}

/**
 * Preferences of the artifact generation form, kept between visits.
 *
 * The kind and its variant are remembered: they are the two selections whose
 * consequence (bullets or prose, with or without diagrams) is not visible in
 * the form itself, so making the user redo them every time is the difference
 * between getting the deliverable they wanted or not. Changing the kind resets
 * the variant, because a variant only means something with its own kind.
 */
export const useArtifactFormStore = create<ArtifactFormState>()(
  persist(
    (set) => ({
      kind: 'report',
      variant: DEFAULT_ARTIFACT_VARIANT.report,
      setKind: (kind) =>
        set((state) => {
          const next = sanitizeKind(kind)
          return next === state.kind
            ? { kind: next }
            : { kind: next, variant: DEFAULT_ARTIFACT_VARIANT[next] }
        }),
      setVariant: (variant) =>
        set((state) => ({ variant: sanitizeVariant(state.kind, variant) })),
    }),
    {
      name: 'artifact-form-storage',
      merge: (persisted, current) => {
        const stored = persisted as Partial<ArtifactFormState> | undefined
        const kind = sanitizeKind(stored?.kind)
        return {
          ...current,
          kind,
          variant: sanitizeVariant(kind, stored?.variant),
        }
      },
    }
  )
)
