import { Credential, UpdateCredentialRequest } from '@/lib/api/credentials'

export interface CredentialFormValues {
  name: string
  apiKey: string
  baseUrl: string
  modalities: string[]
  project: string
  location: string
  credentialsPath: string
  numCtx: string
  isVertex: boolean
  isOllama: boolean
}

/**
 * Build the partial-update payload for PUT /credentials/{id} from the edit
 * form state: only changed fields are included, and a field the user emptied
 * is sent as an explicit `null` so the server actually clears it. `undefined`
 * must never be used for a change — JSON.stringify drops the key and the
 * server's partial-update semantics would silently keep the old value.
 */
export function buildCredentialUpdatePayload(
  credential: Credential,
  values: CredentialFormValues,
): UpdateCredentialRequest {
  const data: UpdateCredentialRequest = {}
  if (values.name !== credential.name) data.name = values.name
  if (values.apiKey.trim()) data.api_key = values.apiKey.trim()
  if (values.baseUrl !== (credential.base_url || '')) data.base_url = values.baseUrl || null
  if (JSON.stringify(values.modalities) !== JSON.stringify(credential.modalities)) {
    data.modalities = values.modalities
  }
  if (values.isVertex) {
    if (values.project !== (credential.project || '')) data.project = values.project.trim() || null
    if (values.location !== (credential.location || '')) data.location = values.location.trim() || null
    if (values.credentialsPath !== (credential.credentials_path || '')) {
      data.credentials_path = values.credentialsPath.trim() || null
    }
  }
  if (values.isOllama && values.numCtx !== (credential.num_ctx ? String(credential.num_ctx) : '')) {
    // empty clears the override (0 -> backend resets to default)
    data.num_ctx = values.numCtx.trim() ? Number(values.numCtx) : 0
  }
  return data
}
