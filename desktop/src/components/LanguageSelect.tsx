import { LANGUAGE_LABELS, SUPPORTED_LANGUAGES, type Language } from "../i18n/languages";

interface LanguageSelectProps {
  value: Language;
  onChange: (language: Language) => void;
  label?: string;
  className?: string;
}

export function LanguageSelect({ value, onChange, label, className = "" }: LanguageSelectProps) {
  return (
    <label className={`block space-y-2 ${className}`}>
      {label ? <span className="text-sm text-slate-300">{label}</span> : null}
      <select
        className="w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none focus:border-sky-400"
        value={value}
        onChange={(e) => onChange(e.target.value as Language)}
      >
        {SUPPORTED_LANGUAGES.map((language) => (
          <option key={language} value={language} className="bg-slate-900">
            {LANGUAGE_LABELS[language]}
          </option>
        ))}
      </select>
    </label>
  );
}
