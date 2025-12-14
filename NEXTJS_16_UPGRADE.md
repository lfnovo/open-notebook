# Next.js 16 Upgrade Complete ✅

**Upgraded on:** December 10, 2025

## Versions

| Package | Before | After |
|---------|--------|-------|
| Next.js | 15.4.7 | **16.0.8** |
| React | 19.1.0 | **19.2.1** |
| React DOM | 19.1.0 | **19.2.1** |
| @types/react | 19 | **19 (latest)** |
| @types/react-dom | 19 | **19 (latest)** |

## Changes Made

### 1. **Removed `--turbopack` flag** (No longer needed in Next.js 16)
```diff
# frontend/package.json
"scripts": {
-  "dev": "next dev --turbopack",
+  "dev": "next dev",
   "build": "next build",
   "start": "next start -p ${PORT:-8502}",
   "lint": "next lint"
}
```

**Reason:** Turbopack is now the default bundler in Next.js 16 for both dev and build.

### 2. **Updated Dependencies**
```bash
docker-compose -f docker-compose.dev.yml exec -T open_notebook sh -c \
  "cd /app/frontend && npm install next@latest react@latest react-dom@latest"
```

## What's New in Next.js 16

### ✨ Key Features

1. **Turbopack by Default**
   - Faster builds (no manual flag needed)
   - Development uses `.next/dev` directory
   - Production uses `.next` directory

2. **React 19.2**
   - View Transitions
   - `useEffectEvent` hook
   - Activity component

3. **Enhanced Routing**
   - Layout deduplication during prefetch
   - Incremental prefetching (only uncached parts)

4. **Caching APIs**
   - `revalidateTag` - stale-while-revalidate semantics
   - `updateTag` - read-your-writes (immediate refresh)
   - `refresh` - refresh client router from Server Actions
   - `cacheLife` and `cacheTag` now stable (no `unstable_` prefix)

5. **React Compiler Support (Stable)**
   - Zero-cost automatic memoization
   - Opt-in via `reactCompiler: true` in config

### 🔧 Breaking Changes (Already Handled)

#### ✅ Async Request APIs (Fully Required)
- All APIs like `cookies()`, `headers()`, `params`, `searchParams` must now be awaited
- **Status:** No usage in your codebase that needs migration

#### ✅ Image Defaults Changed
- `minimumCacheTTL`: 60s → **4 hours** (14400s)
- `imageSizes`: Removed `16` from default array
- `qualities`: Default now only `[75]` instead of all
- `maximumRedirects`: Unlimited → **3 max**
- **Status:** Using defaults is fine

#### ✅ `middleware` → `proxy` Rename
- **Status:** No middleware file in your project

#### ✅ Parallel Routes Require `default.js`
- **Status:** No parallel routes (@slot) detected

### 📊 Performance Improvements

- **Concurrent dev and build:** Can run `next dev` and `next build` simultaneously
- **Faster config loading:** Next config loaded once instead of twice
- **Better terminal output:** Clearer formatting and metrics

## Verification

✅ Frontend accessible at http://localhost:8502  
✅ Next.js 16.0.8 confirmed via `npm list next`  
✅ Turbopack chunk names visible in HTML (`[turbopack]`)  
✅ No build errors  
✅ Hot reload working  

## Notes

- No code changes required for basic functionality
- All Tailwind CSS v4 features remain compatible
- Anki feature working with deck creation
- React Query and all UI components compatible

## If Issues Occur

### Rollback to Next.js 15
```bash
docker-compose -f docker-compose.dev.yml exec -T open_notebook sh -c \
  "cd /app/frontend && npm install next@15.4.7"
```

Then restore the `--turbopack` flag in package.json scripts.

### Opting Out of Turbopack
If you need to use Webpack for production:
```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build --webpack"
  }
}
```

## Resources

- [Next.js 16 Upgrade Guide](https://nextjs.org/docs/app/guides/upgrading/version-16)
- [React 19.2 Announcement](https://react.dev/blog/2025/10/01/react-19-2)
- [Turbopack Documentation](https://nextjs.org/docs/app/api-reference/turbopack)
