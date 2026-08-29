import { describe, it, expect } from 'vitest'
import { QUICK_PROMPTS, buildQuickPrompt } from './quick-prompts'

const interactiveQuiz = QUICK_PROMPTS.find((t) => t.id === 'interactive_quiz')!
const examSimulation = QUICK_PROMPTS.find((t) => t.id === 'exam_simulation')!
const tutorPersona = QUICK_PROMPTS.find((t) => t.id === 'tutor_persona')!
const summaryContradictions = QUICK_PROMPTS.find((t) => t.id === 'summary_contradictions')!

describe('buildQuickPrompt', () => {
  it('substitutes all fields when every value is provided', () => {
    const result = buildQuickPrompt(interactiveQuiz, {
      tema: 'la Revolución Francesa',
      cantidad: '8',
    })
    expect(result).toContain('sobre la Revolución Francesa')
    expect(result).toContain('Hazme 8 preguntas')
    expect(result).not.toContain('{tema}')
    expect(result).not.toContain('{cantidad}')
  })

  it('falls back to the field default when an optional field is left blank', () => {
    const result = buildQuickPrompt(interactiveQuiz, {
      tema: '',
      cantidad: '',
    })
    expect(result).toContain('sobre todo el contenido de este notebook')
    expect(result).toContain('Hazme 5 preguntas')
    expect(result).not.toContain('{tema}')
    expect(result).not.toContain('{cantidad}')
  })

  it('falls back to defaults when values are entirely missing (not just blank)', () => {
    const result = buildQuickPrompt(interactiveQuiz, {})
    expect(result).toContain('todo el contenido de este notebook')
    expect(result).not.toContain('{tema}')
    expect(result).not.toContain('{cantidad}')
  })

  it('trims whitespace-only input and falls back to the default', () => {
    const result = buildQuickPrompt(interactiveQuiz, { tema: '   ', cantidad: '5' })
    expect(result).toContain('sobre todo el contenido de este notebook')
  })

  it('returns the body unchanged for a template with no fields', () => {
    const result = buildQuickPrompt(summaryContradictions, {})
    expect(result).toBe(summaryContradictions.body)
  })

  it('substitutes select-field literal values verbatim (exam simulation)', () => {
    const result = buildQuickPrompt(examSimulation, {
      tema: 'termodinámica',
      cantidad: '15',
      tipo: 'opción múltiple',
    })
    expect(result).toContain('con 15 preguntas de tipo opción múltiple')
  })

  it('uses select defaults when left unset (exam simulation)', () => {
    const result = buildQuickPrompt(examSimulation, { tema: '', cantidad: '', tipo: '' })
    expect(result).toContain('con 10 preguntas de tipo mixto (opción múltiple y desarrollo)')
  })

  it('has no default for a required field with no defaultValue (tutor persona)', () => {
    const materiaField = tutorPersona.fields.find((f) => f.key === 'materia')!
    expect(materiaField.required).toBe(true)
    expect(materiaField.defaultValue).toBeUndefined()

    const result = buildQuickPrompt(tutorPersona, { materia: '', estilo: '' })
    // No default to fall back to, so the token resolves to an empty string.
    expect(result).toContain('tutor personal de  para este notebook')
    expect(result).toContain('estilo debe ser paciente y motivador')
  })
})
