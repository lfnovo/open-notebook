# Fuse.js

![Node.js CI](https://github.com/krisk/Fuse/workflows/Node.js%20CI/badge.svg)
[![Version](https://img.shields.io/npm/v/fuse.js.svg)](https://www.npmjs.com/package/fuse.js)
[![Downloads](https://img.shields.io/npm/dm/fuse.js.svg)](https://npmcharts.com/compare/fuse.js?minimal=tru)
[![code style: prettier](https://img.shields.io/badge/code_style-prettier-ff69b4.svg?style=flat-square)](https://github.com/prettier/prettier)
[![Contributors](https://img.shields.io/github/contributors/krisk/fuse.svg)](https://github.com/krisk/Fuse/graphs/contributors)
![License](https://img.shields.io/npm/l/fuse.js.svg)

Fuse.js is a lightweight, zero-dependency fuzzy-search library written in TypeScript. It works in the browser and on the server, and is designed for searching small-to-medium datasets on the client side where you can't rely on a dedicated search backend.

## ✨ What's New: Token Search

Multi-word fuzzy search with relevance ranking. Type `"javascrpt paterns"` and find `"JavaScript Patterns"` — typo tolerance, multiple words, and smart ranking all at once.

```js
const fuse = new Fuse(docs, {
  useTokenSearch: true,
  keys: ['title', 'author', 'description']
})

fuse.search('javascrpt paterns')
// → [{ item: { title: 'JavaScript Patterns', ... } }]
```

See [Token Search](#token-search) below for details.

## Installation

```bash
npm install fuse.js
```

```bash
yarn add fuse.js
```

Or include directly via CDN:

```html
<script src="https://cdn.jsdelivr.net/npm/fuse.js/dist/fuse.min.mjs"></script>
```

## Quick Start

```js
import Fuse from 'fuse.js'

const books = [
  { title: "Old Man's War", author: 'John Scalzi' },
  { title: 'The Lock Artist', author: 'Steve Hamilton' },
  { title: 'HTML5', author: 'Remy Sharp' },
  { title: 'JavaScript: The Good Parts', author: 'Douglas Crockford' }
]

const fuse = new Fuse(books, {
  keys: ['title', 'author']
})

fuse.search('javscript')
// → [{ item: { title: 'JavaScript: The Good Parts', ... }, ... }]
```

## Features

### Fuzzy Search

The core of Fuse.js. Uses the [Bitap algorithm](https://en.wikipedia.org/wiki/Bitap_algorithm) for approximate string matching — handles typos, misspellings, and partial matches out of the box.

```js
fuse.search('javscript')
// → [{ item: { title: 'JavaScript: The Good Parts', author: 'Douglas Crockford' } }]
```

### Weighted Keys

Search across multiple fields with different importance levels. Title matches can rank higher than description matches.

```js
const fuse = new Fuse(docs, {
  keys: [
    { name: 'title', weight: 2 },
    { name: 'description', weight: 1 }
  ]
})
```

### Extended Search

Use operators for precise control: exact match (`=`), prefix (`^`), suffix (`!`), and more. Enable with `useExtendedSearch: true`.

```js
const fuse = new Fuse(list, {
  useExtendedSearch: true,
  keys: ['title']
})

fuse.search('=exact match')   // exact match
fuse.search('^prefix')        // starts with
fuse.search('!term')          // does not include
```

### Token Search

Splits multi-word queries into individual terms, fuzzy-matches each independently, and ranks results using BM25-style IDF weighting. Enable with `useTokenSearch: true`.

```js
const fuse = new Fuse(docs, {
  useTokenSearch: true,
  keys: ['title', 'body']
})

fuse.search('express midleware rout')
// Finds "Express Middleware" and "Express Routing Guide" despite typos
```

- **Typo tolerance per word** — each term is fuzzy-matched independently
- **Relevance ranking** — rare terms are weighted higher than common ones
- **Word order independent** — `"patterns javascript"` and `"javascript patterns"` return identical results
- **No query length limit** — long multi-word queries work naturally since each term is searched separately

Available in the full build. See [TOKEN_SEARCH.md](TOKEN_SEARCH.md) for details and performance benchmarks.

### Logical Search

Combine conditions with `$and` and `$or` for complex queries. Available in the full build.

```js
fuse.search({
  $and: [
    { title: 'javascript' },
    { author: 'crockford' }
  ]
})
```

### Match Highlighting

Get character-level match indices for highlighting search results in your UI.

```js
const fuse = new Fuse(list, {
  includeMatches: true,
  keys: ['title']
})

const result = fuse.search('javscript')
// result[0].matches[0].indices → [[0, 9]]
```

### Single String Matching

Use `Fuse.match()` to fuzzy-match a pattern against a single string without creating an index. Useful for one-off comparisons or custom filtering.

```js
const result = Fuse.match('javscript', 'JavaScript: The Good Parts')
// → { isMatch: true, score: 0.04, indices: [[0, 9]] }
```

### Dynamic Collections

Add and remove documents from a live index without rebuilding.

```js
fuse.add({ title: 'New Book', author: 'New Author' })
fuse.remove((doc) => doc.title === 'Old Book')
```

## Builds

Fuse.js ships in two variants:

| Build | Includes | Min + gzip |
|---|---|---|
| **Full** | Fuzzy + Extended + Logical + Token search | ~8 kB |
| **Basic** | Fuzzy search only | ~6.5 kB |

Use the basic build if you only need fuzzy search and want the smallest bundle size.

## Documentation

For the full API reference, configuration options, scoring theory, and interactive demos, visit **[fusejs.io](https://fusejs.io)**.

## Supporting Fuse.js

- [Become a backer or sponsor on **GitHub**](https://github.com/sponsors/krisk)
- [Become a backer or sponsor on **Patreon**](https://patreon.com/fusejs)
- [One-time donation via **PayPal**](https://www.paypal.me/kirorisk)

## Develop

See [DEVELOPERS.md](DEVELOPERS.md) for setup, scripts, and project structure.

## Contribute

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on issues and pull requests.
