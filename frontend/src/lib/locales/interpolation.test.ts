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

  it.each([
    [0, 'لا تستخدمه أي حلقة'],
    [1, 'تستخدمه حلقة واحدة'],
    [2, 'تستخدمه حلقتان'],
    [3, 'تستخدمه 3 حلقات'],
    [10, 'تستخدمه 10 حلقات'],
    [11, 'تستخدمه 11 حلقة'],
    [99, 'تستخدمه 99 حلقة'],
    [100, 'تستخدمه 100 حلقة'],
    [101, 'تستخدمه 101 حلقة'],
    [102, 'تستخدمه 102 حلقة'],
    [103, 'تستخدمه 103 حلقات'],
    [1.5, 'تستخدمه 1.5 حلقة'],
  ])('uses the Arabic plural form for %s episodes', (count, expected) => {
    expect(i18n.t('podcasts.usedByCount', { count, lng: 'ar-SA' })).toBe(expected)
  })

  it.each([
    ['fr-FR', 0, 'Utilisé par 0 épisodes'],
    ['pt-BR', 0, 'Usado por 0 episódios'],
    ['bn-IN', 0, '0টি এপিসোড দ্বারা ব্যবহৃত'],
    ['bn-IN', 1, '1টি এপিসোড দ্বারা ব্যবহৃত'],
    ['bn-IN', 2, '2টি এপিসোড দ্বারা ব্যবহৃত'],
    ['ru-RU', 1, 'Используется в 1 эпизоде'],
    ['ru-RU', 2, 'Используется в 2 эпизодах'],
    ['ru-RU', 5, 'Используется в 5 эпизодах'],
    ['ru-RU', 21, 'Используется в 21 эпизоде'],
    ['ru-RU', 31, 'Используется в 31 эпизоде'],
    ['ru-RU', 101, 'Используется в 101 эпизоде'],
    ['pl-PL', 1, 'Używany przez 1 odcinek'],
    ['pl-PL', 2, 'Używany przez 2 odcinki'],
    ['pl-PL', 3, 'Używany przez 3 odcinki'],
    ['pl-PL', 4, 'Używany przez 4 odcinki'],
    ['pl-PL', 5, 'Używany przez 5 odcinków'],
    ['pl-PL', 12, 'Używany przez 12 odcinków'],
    ['pl-PL', 22, 'Używany przez 22 odcinki'],
    ['pl-PL', 24, 'Używany przez 24 odcinki'],
    ['pl-PL', 25, 'Używany przez 25 odcinków'],
  ])('renders %s episode count %s', (lng, count, expected) => {
    expect(i18n.t('podcasts.usedByCount', { count, lng })).toBe(expected)
  })

  // These labels express a total, not a number followed by an inflected noun.
  // Exercise the rendered output across all Arabic plural categories, including
  // zero, where i18next can otherwise select an explicit _zero override.
  describe.each([
    ['sources.insightsCount', 'عدد الرؤى: ', ''],
    ['notebooks.deleteNotebookNotes', 'عدد الملاحظات التي ستُحذف نهائيًا: ', '.'],
    ['common.individualAnswers', 'عدد الإجابات الفردية: ', ''],
    ['models.autoAssignSuccess', 'عدد النماذج الافتراضية التي تم تعيينها تلقائيًا: ', ''],
  ])('Arabic count label %s', (key, label, suffix) => {
    it.each([0, 1, 2, 3, 10, 11, 99, 100, 101, 102, 103, 1.5])('renders count %s', count => {
      expect(i18n.t(key, { count, lng: 'ar-SA' })).toBe(`${label}${count}${suffix}`)
    })
  })

  describe('search result counts (#1402)', () => {
    it.each([
      ['en-US', 0, '0 results found'],
      ['en-US', 1, '1 result found'],
      ['en-US', 2, '2 results found'],
      ['de-DE', 1, '1 Ergebnis gefunden'],
      ['de-DE', 2, '2 Ergebnisse gefunden'],
      ['fr-FR', 0, '0 résultat trouvé'],
      ['fr-FR', 1, '1 résultat trouvé'],
      ['fr-FR', 2, '2 résultats trouvés'],
      ['it-IT', 1, '1 risultato trovato'],
      ['it-IT', 2, '2 risultati trovati'],
      ['es-ES', 1, '1 resultado encontrado'],
      ['es-ES', 2, '2 resultados encontrados'],
      ['pt-BR', 0, '0 resultado encontrado'],
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

    // Arabic selects all six plural categories. fallbackLng is off so a
    // missing form fails here instead of rendering the English text.
    it.each([
      [0, 'لم يتم العثور على نتائج'],
      [1, 'تم العثور على نتيجة واحدة'],
      [2, 'تم العثور على نتيجتين'],
      [3, 'تم العثور على 3 نتائج'],
      [10, 'تم العثور على 10 نتائج'],
      [11, 'تم العثور على 11 نتيجة'],
      [99, 'تم العثور على 99 نتيجة'],
      [100, 'تم العثور على 100 نتيجة'],
      [101, 'تم العثور على 101 نتيجة'],
      [102, 'تم العثور على 102 نتيجة'],
      [103, 'تم العثور على 103 نتائج'],
      [1.5, 'تم العثور على 1.5 نتيجة'],
    ])('ar-SA with count %s renders %s', (count, expected) => {
      expect(
        i18n.t('searchPage.resultsFound', { lng: 'ar-SA', count, fallbackLng: false }),
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
