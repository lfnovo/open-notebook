export const I18N_LANGUAGE_CHANGE_START = 'i18n:language-change-start'
export const I18N_LANGUAGE_CHANGE_END = 'i18n:language-change-end'

type LanguageChangeDetail = {
  language: string
}

export const i18nEvents = new EventTarget()

export function emitLanguageChangeStart(language: string) {
  i18nEvents.dispatchEvent(
    new CustomEvent<LanguageChangeDetail>(I18N_LANGUAGE_CHANGE_START, {
      detail: { language },
    })
  )
}

export function emitLanguageChangeEnd(language: string) {
  i18nEvents.dispatchEvent(
    new CustomEvent<LanguageChangeDetail>(I18N_LANGUAGE_CHANGE_END, {
      detail: { language },
    })
  )
}
