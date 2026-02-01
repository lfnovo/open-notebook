import { describe, it, expect } from 'vitest'
import { enUS } from './en-US'
import { zhCN } from './zh-CN'
import { zhTW } from './zh-TW'
import { jaJP } from './ja-JP'
import { ruRU } from './ru-RU'

describe('Internationalization Locales Integrity', () => {
  const getKeys = (obj: Record<string, unknown>, prefix = ''): string[] => {
    return Object.keys(obj).reduce((res: string[], el) => {
      const val = obj[el]
      if (typeof val === 'object' && val !== null && !Array.isArray(val)) {
        return [...res, ...getKeys(val as Record<string, unknown>, prefix + el + '.')]
      }
      return [...res, prefix + el]
    }, [])
  }

  const enKeys = getKeys(enUS)
  const zhCNKeys = getKeys(zhCN)
  const zhTWKeys = getKeys(zhTW)
  const jaJPKeys = getKeys(jaJP)
  const ruRUKeys = getKeys(ruRU)

  it('zh-CN should have the same keys as en-US', () => {
    const missingInZhCN = enKeys.filter(key => !zhCNKeys.includes(key))
    const extraInZhCN = zhCNKeys.filter(key => !enKeys.includes(key))

    expect(missingInZhCN, `Missing keys in zh-CN: ${missingInZhCN.join(', ')}`).toEqual([])
    expect(extraInZhCN, `Extra keys in zh-CN: ${extraInZhCN.join(', ')}`).toEqual([])
  })

  it('zh-TW should have the same keys as en-US', () => {
    const missingInZhTW = enKeys.filter(key => !zhTWKeys.includes(key))
    const extraInZhTW = zhTWKeys.filter(key => !enKeys.includes(key))

    expect(missingInZhTW, `Missing keys in zh-TW: ${missingInZhTW.join(', ')}`).toEqual([])
    expect(extraInZhTW, `Extra keys in zh-TW: ${extraInZhTW.join(', ')}`).toEqual([])
  })

  it('ja-JP should have the same keys as en-US', () => {
    const missingInJaJP = enKeys.filter(key => !jaJPKeys.includes(key))
    const extraInJaJP = jaJPKeys.filter(key => !enKeys.includes(key))

    expect(missingInJaJP, `Missing keys in ja-JP: ${missingInJaJP.join(', ')}`).toEqual([])
    expect(extraInJaJP, `Extra keys in ja-JP: ${extraInJaJP.join(', ')}`).toEqual([])
  })

  it('ru-RU should have the same keys as en-US', () => {
    const missingInRuRU = enKeys.filter(key => !ruRUKeys.includes(key))
    const extraInRuRU = ruRUKeys.filter(key => !enKeys.includes(key))

    expect(missingInRuRU, `Missing keys in ru-RU: ${missingInRuRU.join(', ')}`).toEqual([])
    expect(extraInRuRU, `Extra keys in ru-RU: ${extraInRuRU.join(', ')}`).toEqual([])
  })
})
