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
    ['searchPage.resultsFound', 'عدد النتائج: ', ''],
    ['common.individualAnswers', 'عدد الإجابات الفردية: ', ''],
    ['models.autoAssignSuccess', 'عدد النماذج الافتراضية التي تم تعيينها تلقائيًا: ', ''],
  ])('Arabic count label %s', (key, label, suffix) => {
    it.each([0, 1, 2, 3, 10, 11, 99, 100, 101, 102, 103, 1.5])('renders count %s', count => {
      expect(i18n.t(key, { count, lng: 'ar-SA' })).toBe(`${label}${count}${suffix}`)
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
