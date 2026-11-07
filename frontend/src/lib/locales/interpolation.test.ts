import { describe, it, expect, beforeAll } from 'vitest'
import { createInstance } from 'i18next'
import { resources } from './index'

// Mirrors the interpolation config in src/lib/i18n.ts
const i18n = createInstance()

beforeAll(async () => {
  await i18n.init({
    resources,
    lng: 'en-US',
    fallbackLng: 'en-US',
    interpolation: {
      escapeValue: false, // react already safes from xss
    },
  })
})

describe('i18next interpolation', () => {
  it('interpolates a single variable', () => {
    expect(i18n.t('chat.chatWith', { name: 'Sources' })).toBe('Chat with Sources')
  })

  it('interpolates multiple variables', () => {
    expect(i18n.t('sources.batchPartial', { success: 2, failed: 1 })).toBe(
      '2 succeeded, 1 failed',
    )
  })

  it('resolves plural forms from the base key', () => {
    expect(i18n.t('podcasts.usedByCount', { count: 1 })).toBe('Used by 1 episode')
    expect(i18n.t('podcasts.usedByCount', { count: 3 })).toBe('Used by 3 episodes')
  })

  describe('search result counts (#1402)', () => {
    it.each([
      ['en-US', 0, '0 results found'],
      ['en-US', 1, '1 result found'],
      ['en-US', 2, '2 results found'],
      ['de-DE', 1, '1 Ergebnis gefunden'],
      ['de-DE', 2, '2 Ergebnisse gefunden'],
      ['fr-FR', 1, '1 résultat trouvé'],
      ['fr-FR', 2, '2 résultats trouvés'],
      ['it-IT', 1, '1 risultato trovato'],
      ['it-IT', 2, '2 risultati trovati'],
      ['es-ES', 1, '1 resultado encontrado'],
      ['es-ES', 2, '2 resultados encontrados'],
      ['pt-BR', 1, '1 resultado encontrado'],
      ['pt-BR', 2, '2 resultados encontrados'],
      ['ca-ES', 1, "S'ha trobat 1 resultat"],
      ['ca-ES', 2, "S'han trobat 2 resultats"],
      ['ru-RU', 0, 'Найдено 0 результатов'],
      ['ru-RU', 1, 'Найден 1 результат'],
      ['ru-RU', 2, 'Найдено 2 результата'],
      ['ru-RU', 5, 'Найдено 5 результатов'],
      ['ru-RU', 11, 'Найдено 11 результатов'],
      ['ru-RU', 21, 'Найден 21 результат'],
      ['ru-RU', 22, 'Найдено 22 результата'],
      ['pl-PL', 0, 'Znaleziono 0 wyników'],
      ['pl-PL', 1, 'Znaleziono 1 wynik'],
      ['pl-PL', 2, 'Znaleziono 2 wyniki'],
      ['pl-PL', 5, 'Znaleziono 5 wyników'],
      ['pl-PL', 12, 'Znaleziono 12 wyników'],
      ['pl-PL', 21, 'Znaleziono 21 wyników'],
      ['pl-PL', 22, 'Znaleziono 22 wyniki'],
      ['bn-IN', 1, '1টি ফলাফল পাওয়া গেছে'],
      ['bn-IN', 2, '2টি ফলাফল পাওয়া গেছে'],
      ['tr-TR', 1, '1 sonuç bulundu'],
      ['tr-TR', 2, '2 sonuç bulundu'],
      ['ja-JP', 1, '1件の結果'],
      ['ja-JP', 2, '2件の結果'],
      ['zh-CN', 1, '1 个结果'],
      ['zh-CN', 2, '2 个结果'],
      ['zh-TW', 1, '1 個結果'],
      ['zh-TW', 2, '2 個結果'],
    ])('%s with count %i renders %s', (lng, count, expected) => {
      expect(
        i18n.t('searchPage.resultsFound', { lng, count, fallbackLng: false }),
      ).toBe(expected)
    })
  })

  it('does not escape interpolated values (React escapes at render)', () => {
    expect(i18n.t('notebooks.deleteNotebookDesc', { name: 'Research & Notes' })).toBe(
      'Are you sure you want to delete "Research & Notes"? This action cannot be undone.',
    )
  })

  it('interpolates in a non-English locale', () => {
    expect(
      i18n.t('sources.selectedCount', { count: 4, lng: 'pt-BR' }),
    ).toContain('4')
  })
})
