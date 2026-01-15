/**
 * Utility to map backend English error messages to i18n keys.
 */
export const ERROR_MAP: Record<string, string> = {
  "Notebook not found": "apiErrors.notebookNotFound",
  "Source not found": "apiErrors.sourceNotFound",
  "Transformation not found": "apiErrors.transformationNotFound",
  "File upload failed": "apiErrors.fileUploadFailed",
  "URL is required for link type": "apiErrors.urlRequired",
  "Content is required for text type": "apiErrors.contentRequired",
  "Invalid source type": "apiErrors.invalidSourceType",
  "Processing failed": "apiErrors.processingFailed",
  "Failed to queue processing": "apiErrors.failedToQueue",
  "sort_by must be 'created' or 'updated'": "apiErrors.invalidSortBy",
  "sort_order must be 'asc' or 'desc'": "apiErrors.invalidSortOrder",
  "Access to file denied": "apiErrors.accessDenied",
  "File not found on server": "apiErrors.fileNotFoundOnServer",
  "Missing authorization": "apiErrors.unauthorized",
  "Invalid password": "apiErrors.invalidPassword",
  "Invalid authorization header format": "apiErrors.unauthorized",
  "Missing authorization header": "apiErrors.unauthorized",
  "Vector search requires an embedding model": "apiErrors.embeddingModelRequired",
  "Ask feature requires an embedding model": "apiErrors.embeddingModelRequired",
  "Strategy model": "apiErrors.strategyModelNotFound",
  "Answer model": "apiErrors.answerModelNotFound",
  "Final answer model": "apiErrors.finalAnswerModelNotFound",
  "No answer generated": "apiErrors.noAnswerGenerated",
};

/**
 * Translates a backend error message using the ERROR_MAP.
 * If no mapping exists, returns the fallback key or generic error key.
 */
export function getApiErrorKey(errorOrMessage: unknown, fallbackKey?: string): string {
  const message = formatApiError(errorOrMessage);
  
  if (!message) return fallbackKey || "apiErrors.genericError";

  // Try exact match first
  if (ERROR_MAP[message]) {
    return ERROR_MAP[message];
  }

  // Try partial match for dynamic messages (e.g., "File upload failed: ...")
  for (const [key, value] of Object.entries(ERROR_MAP)) {
    if (message.startsWith(key)) {
      return value;
    }
  }

  return fallbackKey || "apiErrors.genericError";
}

/**
 * Formats a raw error from the API into a user-friendly (potentially translated) string.
 */
export function formatApiError(error: unknown): string {
  if (typeof error === 'string') return error;
  
  const err = error as { response?: { data?: { detail?: string } }, detail?: string, message?: string };
  const detail = err?.response?.data?.detail || err?.detail || err?.message;
  
  if (typeof detail === 'string') {
    return detail; // We'll handle the actual translation using the key in the hook/component
  }
  
  return "An unexpected error occurred";
}
