export type Language = "de" | "en";

export const SUPPORTED_LANGUAGES: Language[] = ["de", "en"];

export const LANGUAGE_LABELS: Record<Language, string> = {
  de: "Deutsch",
  en: "English",
};

export function normalizeLanguage(value: string | undefined | null): Language {
  if (!value) return "en";
  const code = value.toLowerCase().split(/[-_]/)[0];
  return code === "de" ? "de" : "en";
}
