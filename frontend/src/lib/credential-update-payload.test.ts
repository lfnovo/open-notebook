import { describe, it, expect } from 'vitest'
import { buildCredentialUpdatePayload, CredentialFormValues } from './credential-update-payload'
import { Credential } from '@/lib/api/credentials'

const credential: Credential = {
  id: 'credential:1',
  name: 'Ollama',
  provider: 'ollama',
  modalities: ['language'],
  base_url: 'http://10.0.0.99:11434',
  project: 'old-project',
  location: 'us-east5',
  credentials_path: '/old/path.json',
  num_ctx: null,
  has_api_key: false,
  created: '2026-01-01',
  updated: '2026-01-01',
  model_count: 0,
}

const values = (overrides: Partial<CredentialFormValues>): CredentialFormValues => ({
  name: credential.name,
  apiKey: '',
  baseUrl: credential.base_url || '',
  modalities: credential.modalities,
  project: credential.project || '',
  location: credential.location || '',
  credentialsPath: credential.credentials_path || '',
  numCtx: '',
  isVertex: false,
  isOllama: true,
  ...overrides,
})

describe('buildCredentialUpdatePayload', () => {
  it('sends explicit null when base_url is emptied (the original bug: undefined was dropped from the JSON body and the stale URL survived)', () => {
    const payload = buildCredentialUpdatePayload(credential, values({ baseUrl: '' }))
    expect(payload).toHaveProperty('base_url')
    expect(payload.base_url).toBeNull()
    // undefined would be stripped by JSON.stringify — the regression this guards against
    expect(JSON.parse(JSON.stringify(payload))).toHaveProperty('base_url')
  })

  it('sends the new value when base_url is changed', () => {
    const payload = buildCredentialUpdatePayload(credential, values({ baseUrl: 'http://localhost:11434' }))
    expect(payload.base_url).toBe('http://localhost:11434')
  })

  it('omits base_url entirely when unchanged', () => {
    const payload = buildCredentialUpdatePayload(credential, values({}))
    expect(payload).not.toHaveProperty('base_url')
  })

  it('sends explicit null for emptied Vertex fields', () => {
    const payload = buildCredentialUpdatePayload(
      credential,
      values({ isVertex: true, project: '', location: '', credentialsPath: '' }),
    )
    expect(payload.project).toBeNull()
    expect(payload.location).toBeNull()
    expect(payload.credentials_path).toBeNull()
    const wire = JSON.parse(JSON.stringify(payload))
    expect(wire).toHaveProperty('project')
    expect(wire).toHaveProperty('location')
    expect(wire).toHaveProperty('credentials_path')
  })

  it('clears the ollama num_ctx override with 0 when emptied', () => {
    const withCtx = { ...credential, num_ctx: 4096 }
    const payload = buildCredentialUpdatePayload(withCtx, values({ numCtx: '' }))
    expect(payload.num_ctx).toBe(0)
  })
})
