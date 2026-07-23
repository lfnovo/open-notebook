import type { KatexOptions } from 'katex'

// AI-generated content often contains Unicode punctuation (en/em dashes,
// smart quotes) inside single-dollar math spans that models emit for
// legitimate inline math (see prompts/*/system.jinja "MATH FORMATTING"
// sections). KaTeX's default strict mode logs a console warning for each
// character outside its symbol table - harmless (it still renders a
// best-effort glyph) but noisy in production logs. Ignore only that specific
// warning; leave every other strict check (e.g. deprecated commands) as-is.
export const KATEX_OPTIONS: KatexOptions = {
  strict: (errorCode) => (errorCode === 'unknownSymbol' ? 'ignore' : 'warn'),
}
