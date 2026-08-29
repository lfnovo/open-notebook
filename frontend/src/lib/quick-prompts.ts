/**
 * Quick Prompts library — static, predefined chat-starter templates for the
 * chat composer. Each template is a conversational/interactive study
 * technique (quiz, exam simulation, tutor persona, summary+contradictions)
 * distinct from the one-shot `Transformation` presets and from the
 * self-explanation suggestion in ChatPanel (see ChatPanel.tsx).
 *
 * IMPORTANT: `body` is the literal instruction text sent to the LLM and is
 * NOT localized — it mirrors the existing precedent of the seeded
 * Transformation presets ("Study Guide", "Feynman Explanation", etc.), which
 * store a single canonical Spanish prompt regardless of UI locale. Only the
 * UI chrome (title/description/field labels/placeholders/option labels) goes
 * through i18n via the *Key fields below.
 */

export interface QuickPromptFieldOption {
  value: string
  labelKey: string
}

export interface QuickPromptField {
  key: string
  type: 'text' | 'select'
  labelKey: string
  placeholderKey?: string
  options?: QuickPromptFieldOption[]
  defaultValue?: string
  required?: boolean
}

export interface QuickPromptTemplate {
  id: string
  titleKey: string
  descriptionKey: string
  fields: QuickPromptField[]
  /** Canonical Spanish prompt body with `{key}` placeholders. Not localized. */
  body: string
}

const DEFAULT_TOPIC = 'todo el contenido de este notebook'

export const QUICK_PROMPTS: QuickPromptTemplate[] = [
  {
    id: 'interactive_quiz',
    titleKey: 'chat.quickPrompts.templates.interactiveQuiz.title',
    descriptionKey: 'chat.quickPrompts.templates.interactiveQuiz.description',
    fields: [
      {
        key: 'tema',
        type: 'text',
        labelKey: 'chat.quickPrompts.fields.topic.label',
        placeholderKey: 'chat.quickPrompts.fields.topic.placeholder',
        defaultValue: DEFAULT_TOPIC,
      },
      {
        key: 'cantidad',
        type: 'select',
        labelKey: 'chat.quickPrompts.fields.questionCount.label',
        options: [
          { value: '3', labelKey: 'chat.quickPrompts.options.count3' },
          { value: '5', labelKey: 'chat.quickPrompts.options.count5' },
          { value: '8', labelKey: 'chat.quickPrompts.options.count8' },
          { value: '10', labelKey: 'chat.quickPrompts.options.count10' },
        ],
        defaultValue: '5',
      },
    ],
    body: 'Actúa como un tutor que me toma un examen oral interactivo sobre {tema}. Hazme {cantidad} preguntas, una por una: espera mi respuesta antes de pasar a la siguiente. Después de cada respuesta, califícala del 1 al 10, explica brevemente qué le faltó o qué estuvo bien, y si mi calificación fue baja no me des la respuesta correcta completa: dame una pista y déjame intentar de nuevo una vez antes de seguir con la siguiente pregunta. Al final, dame un resumen de mi desempeño y qué temas debo repasar.',
  },
  {
    id: 'exam_simulation',
    titleKey: 'chat.quickPrompts.templates.examSimulation.title',
    descriptionKey: 'chat.quickPrompts.templates.examSimulation.description',
    fields: [
      {
        key: 'tema',
        type: 'text',
        labelKey: 'chat.quickPrompts.fields.topic.label',
        placeholderKey: 'chat.quickPrompts.fields.topic.placeholder',
        defaultValue: DEFAULT_TOPIC,
      },
      {
        key: 'cantidad',
        type: 'select',
        labelKey: 'chat.quickPrompts.fields.questionCount.label',
        options: [
          { value: '5', labelKey: 'chat.quickPrompts.options.count5' },
          { value: '10', labelKey: 'chat.quickPrompts.options.count10' },
          { value: '15', labelKey: 'chat.quickPrompts.options.count15' },
        ],
        defaultValue: '10',
      },
      {
        key: 'tipo',
        type: 'select',
        labelKey: 'chat.quickPrompts.fields.questionType.label',
        options: [
          { value: 'opción múltiple', labelKey: 'chat.quickPrompts.options.typeMultipleChoice' },
          { value: 'preguntas de desarrollo', labelKey: 'chat.quickPrompts.options.typeOpenEnded' },
          { value: 'mixto (opción múltiple y desarrollo)', labelKey: 'chat.quickPrompts.options.typeMixed' },
        ],
        defaultValue: 'mixto (opción múltiple y desarrollo)',
      },
    ],
    body: 'Simula un examen formal sobre {tema} con {cantidad} preguntas de tipo {tipo}, basado estrictamente en el contenido de este notebook. Preséntame todas las preguntas juntas, numeradas, sin mostrarme las respuestas. Cuando te diga que ya terminé o te dé mis respuestas, corrige el examen completo, dame una calificación final y explícame qué respondí mal y por qué.',
  },
  {
    id: 'tutor_persona',
    titleKey: 'chat.quickPrompts.templates.tutorPersona.title',
    descriptionKey: 'chat.quickPrompts.templates.tutorPersona.description',
    fields: [
      {
        key: 'materia',
        type: 'text',
        labelKey: 'chat.quickPrompts.fields.subject.label',
        placeholderKey: 'chat.quickPrompts.fields.subject.placeholder',
        required: true,
      },
      {
        key: 'estilo',
        type: 'select',
        labelKey: 'chat.quickPrompts.fields.style.label',
        options: [
          { value: 'paciente y motivador', labelKey: 'chat.quickPrompts.options.styleFriendly' },
          { value: 'estricto y exigente', labelKey: 'chat.quickPrompts.options.styleStrict' },
          { value: 'directo y breve', labelKey: 'chat.quickPrompts.options.styleDirect' },
        ],
        defaultValue: 'paciente y motivador',
      },
    ],
    body: 'A partir de ahora, actúa como mi tutor personal de {materia} para este notebook. Tu estilo debe ser {estilo}. Basa siempre tus respuestas en el contenido de las fuentes de este notebook, y si te pregunto algo que no está en las fuentes, dime claramente que no está cubierto en el material antes de responder con conocimiento general. Recuérdame de vez en cuando que puedo pedirte flashcards, un quiz o un examen simulado sobre lo que llevamos viendo.',
  },
  {
    id: 'summary_contradictions',
    titleKey: 'chat.quickPrompts.templates.summaryContradictions.title',
    descriptionKey: 'chat.quickPrompts.templates.summaryContradictions.description',
    fields: [],
    body: 'Resume las ideas principales de las fuentes de este notebook y señala específicamente si existe alguna contradicción, inconsistencia o cambio de postura entre las distintas fuentes o secciones. Si encuentras contradicciones, indica exactamente de qué fuente o sección viene cada versión.',
  },
]

/**
 * Substitutes `{key}` tokens in `template.body` with trimmed values from
 * `values`. A blank/missing value falls back to the field's `defaultValue`
 * (or an empty string if none is set). Pure — does no i18n lookups.
 */
export function buildQuickPrompt(
  template: QuickPromptTemplate,
  values: Record<string, string>
): string {
  return template.fields.reduce((text, field) => {
    const raw = values[field.key]?.trim()
    const resolved = raw ? raw : field.defaultValue ?? ''
    return text.split(`{${field.key}}`).join(resolved)
  }, template.body)
}
