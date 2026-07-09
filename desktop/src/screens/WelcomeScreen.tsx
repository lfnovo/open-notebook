import { LANGUAGE_LABELS, type Language } from "../i18n/languages";
import { useI18n } from "../i18n";
import { LanguageSelect } from "../components/LanguageSelect";
import { HeroGraphic } from "../components/HeroGraphic";
import { Button, Card, ScreenShell } from "../components/ui";

interface WelcomeScreenProps {
  language: Language;
  onLanguageChange: (language: Language) => void;
  onContinue: () => void;
}

export function WelcomeScreen({ language, onLanguageChange, onContinue }: WelcomeScreenProps) {
  const { t } = useI18n();

  return (
    <ScreenShell title={t("welcome.title")} subtitle={t("welcome.subtitle")}>
      <div className="mb-6 flex justify-center">
        <HeroGraphic size={160} />
      </div>
      <Card className="space-y-6">
        <LanguageSelect
          label={t("common.language")}
          value={language}
          onChange={onLanguageChange}
        />
        <p className="text-sm text-slate-400">
          {t("welcome.detectedLanguage", { language: LANGUAGE_LABELS[language] })}
        </p>
        <div className="space-y-3 text-slate-300">
          <p>{t("welcome.expectedTitle")}</p>
          <ul className="list-disc space-y-2 pl-5">
            <li>{t("welcome.item1")}</li>
            <li>{t("welcome.item2")}</li>
            <li>{t("welcome.item3")}</li>
          </ul>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/20 p-4 text-sm text-slate-400">
          {t("welcome.license")}
        </div>
        <Button onClick={onContinue}>{t("welcome.startSetup")}</Button>
      </Card>
    </ScreenShell>
  );
}
