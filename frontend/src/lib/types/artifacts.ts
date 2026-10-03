export type ArtifactKind = 'report' | 'deck'

/**
 * Sub-variant of a kind, named after what the deliverable IS.
 *
 * A report is either a plain `document` (prose only) or an `illustrated`
 * document (prose plus diagrams); a deck is either `presenter` slides
 * (concise bullets) or a `detailed` deck (full sentences per bullet).
 */
export type ArtifactVariant = 'document' | 'illustrated' | 'presenter' | 'detailed'

/** Variants accepted per kind. Mirrors `VARIANTS` in the Python outline. */
export const ARTIFACT_VARIANTS: Record<ArtifactKind, readonly ArtifactVariant[]> = {
  report: ['document', 'illustrated'],
  deck: ['presenter', 'detailed'],
}

/** The variant used when the user does not pick one. */
export const DEFAULT_ARTIFACT_VARIANT: Record<ArtifactKind, ArtifactVariant> = {
  report: 'document',
  deck: 'presenter',
}

/**
 * Coerce a value that came from the user or from storage to a valid variant.
 *
 * A persisted value outlives the code that wrote it, and a variant only means
 * something together with a kind (`presenter` belongs to a deck), so an entry
 * that does not belong to the current kind falls back to that kind's default
 * instead of reaching the API, which would reject it with a 400.
 */
export function sanitizeVariant(
  kind: ArtifactKind,
  variant: unknown,
): ArtifactVariant {
  const allowed = ARTIFACT_VARIANTS[kind] as readonly unknown[]
  return allowed.includes(variant)
    ? (variant as ArtifactVariant)
    : DEFAULT_ARTIFACT_VARIANT[kind]
}

export type ArtifactFormat = 'md' | 'html' | 'docx' | 'pptx'

/** One generated report or deck, plus the status of its generating job. */
export interface Artifact {
  id: string
  notebook_id: string
  title: string
  kind: ArtifactKind
  variant?: ArtifactVariant | null
  formats: ArtifactFormat[]
  language: string
  sections: number
  output_path?: string | null
  note_id?: string | null
  created?: string | null
  job_status?: string | null
  error_message?: string | null
  download_url?: string | null
  files: string[]
}

export interface GenerateArtifactRequest {
  notebook_id: string
  kind?: ArtifactKind
  variant?: ArtifactVariant
  formats?: ArtifactFormat[]
  language?: string
  title?: string
  instructions?: string
  sections?: number
}

export interface GenerateArtifactResponse {
  command_id: string
  artifact_id: string
  status: string
}

/** Job statuses that mean "the worker is still working on this". */
export const ACTIVE_ARTIFACT_STATUSES = [
  'pending',
  'running',
  'processing',
  'submitted',
  'queued',
  'new',
] as const
