# Locales Module (i18n)

Internationalization system providing multi-language UI support using i18next with standard `t()` function calls.

## Architecture

```
lib/
├── i18n.ts              # i18next initialization and configuration
├── i18n-events.ts       # Language change event emitters
├── hooks/
│   └── use-translation.ts  # Thin wrapper around react-i18next with language change events
├── utils/
│   └── date-locale.ts   # date-fns locale mapping
└── locales/
    ├── index.ts         # Locale registry and type exports
    ├── en-US/index.ts   # English translations
    ├── pt-BR/index.ts   # Brazilian Portuguese translations
    ├── zh-CN/index.ts   # Simplified Chinese translations
    ├── zh-TW/index.ts   # Traditional Chinese translations
    ├── ja-JP/index.ts   # Japanese translations
    ├── ru-RU/index.ts   # Russian translations
    └── bn-IN/index.ts   # Bengali translations
```

## Key Components

- **`i18n.ts`**: i18next initialization with language detection (localStorage → browser)
- **`i18n-events.ts`**: Event emitters for language change start/end (used by loading overlay)
- **`locales/index.ts`**: Central registry exporting all locales and `LanguageCode` type
- **`use-translation.ts`**: Thin wrapper around react-i18next returning `{ t, i18n, language, setLanguage }`

## Translation Structure

Each locale file exports a flat object with nested keys:

```typescript
export const enUS = {
  common: {
    save: 'Save',
    cancel: 'Cancel',
    delete: 'Delete',
    // ...
  },
  notebooks: {
    title: 'Notebooks',
    createNew: 'Create Notebook',
    // ...
  },
  // ... other sections
}
```

**Sections**:
- `common`: Shared UI elements (buttons, labels, actions)
- `notebooks`, `sources`, `notes`: Feature-specific strings
- `chat`, `search`, `podcasts`: Module-specific strings
- `models`, `transformations`, `settings`: Configuration UI
- `advanced`: System administration strings
- `apiErrors`: Backend error message translations

## Usage Pattern

```typescript
import { useTranslation } from '@/lib/hooks/use-translation'

function MyComponent() {
  const { t, language, setLanguage } = useTranslation()

  // Standard t() function call
  return <h1>{t('notebooks.title')}</h1>

  // With string interpolation
  return <p>{t('common.updated').replace('{time}', timeAgo)}</p>

  // Change language
  await setLanguage('zh-CN')
}
```

### Functions that accept t as a parameter

Use `TFunction` from i18next:

```typescript
import type { TFunction } from 'i18next'

const getNavigation = (t: TFunction) => [
  { name: t('navigation.sources'), href: '/sources' },
]
```

## Important Patterns

- **Standard t() calls**: `t('section.key')` — standard react-i18next pattern
- **Language persistence**: Saved to localStorage, auto-detected on load
- **Fallback**: Falls back to `en-US` if key missing in current locale
- **Date localization**: Use `getDateLocale(language)` from `utils/date-locale.ts`
- **Language change events**: `setLanguage` emits start/end events for `LanguageLoadingOverlay`

## Key Dependencies

- `i18next`: Core internationalization framework
- `react-i18next`: React bindings for i18next
- `i18next-browser-languagedetector`: Auto-detect browser language
- `date-fns/locale`: Date formatting locales

## How to Add a New Language

1. Create locale folder: `locales/pt-BR/index.ts`
2. Copy structure from `en-US/index.ts` and translate all strings
3. Register in `locales/index.ts`:
   ```typescript
   import { ptBR } from './pt-BR'
   export const resources = {
     // ...existing
     'pt-BR': { translation: ptBR },
   }
   export const languages: Language[] = [
     // ...existing
     { code: 'pt-BR', label: 'Português' },
   ]
   ```
4. Add to `utils/date-locale.ts`:
   ```typescript
   import { ptBR } from 'date-fns/locale'
   const LOCALE_MAP = { ...existing, 'pt-BR': ptBR }
   ```

## Important Quirks & Gotchas

- **Language change events**: `emitLanguageChangeStart/End` used by `LanguageLoadingOverlay` for UX
- **No SSR**: `useSuspense: false` disables React Suspense for i18next (avoids hydration issues)
- **All keys required**: Missing keys in non-English locales fall back to English; keep locales in sync
- **ErrorBoundary**: Uses raw `enUS` locale object directly (class component, can't use hooks)

## Testing Patterns

```typescript
// Mock useTranslation in tests (see test/setup.ts)
vi.mock('@/lib/hooks/use-translation', () => ({
  useTranslation: () => ({
    t: (key: string) => key,  // Identity function returns the key
    language: 'en-US',
    setLanguage: vi.fn(),
  }),
}))

// Test locale completeness
import { enUS, zhCN } from '@/lib/locales'
const enKeys = Object.keys(flatten(enUS))
const zhKeys = Object.keys(flatten(zhCN))
expect(zhKeys).toEqual(enKeys)  // All keys present
```
