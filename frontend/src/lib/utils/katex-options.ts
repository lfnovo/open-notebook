import type { KatexOptions } from 'katex'

// AI-generated content often contains Unicode punctuation (en/em dashes,
// smart quotes) inside single-dollar math spans that models emit for
// legitimate inline math (see prompts/*/system.jinja "MATH FORMATTING"
// sections). KaTeX's default strict mode logs a console warning for each
// character outside its symbol table. It still renders - falling back to
// text-mode handling for that character (see katex's Parser: unknown
// codepoints get `mode: 'text'` instead of proper math-mode metrics) - so
// this is not universally cosmetic: an unrecognized symbol can come out
// with approximated spacing/metrics rather than a "real" glyph. Acceptable
// for stray punctuation like a dash; don't extend this ignore to justify
// dumping arbitrary Unicode into math mode. Every other strict check (e.g.
// deprecated commands) is untouched.
export const KATEX_OPTIONS: KatexOptions = {
  strict: (errorCode) => (errorCode === 'unknownSymbol' ? 'ignore' : 'warn'),
}
