import 'vitest'
import type { TestingLibraryMatchers } from '@testing-library/jest-dom/matchers'

// vitest 5 gave Assertion a second type parameter, so the augmentation that
// @testing-library/jest-dom ships (written for Assertion<T>) no longer merges.
// Matchers<R, T> is vitest's extension point for custom matchers.
declare module 'vitest' {
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type, @typescript-eslint/no-unused-vars
  interface Matchers<R extends void | Promise<void> = void | Promise<void>, T = unknown>
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    extends TestingLibraryMatchers<any, R> {}
}
