import { useEffect, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { HeroGraphic } from "../components/HeroGraphic";
import { useI18n } from "../i18n";
import type { LaunchProgress, LaunchPhase } from "../types";

function isLaunchPhase(value: string): value is LaunchPhase {
  return [
    "checkingDocker",
    "checkingStack",
    "pullingImages",
    "startingStack",
    "containersStarting",
    "waitingUi",
    "opening",
    "ready",
  ].includes(value);
}

export function StartScreen() {
  const { t } = useI18n();
  const [progress, setProgress] = useState<LaunchProgress>({
    percent: 0,
    phase: "checkingDocker",
  });

  useEffect(() => {
    const unlistenProgress = listen<LaunchProgress>("launch-progress", (event) => {
      setProgress(event.payload);
    });

    return () => {
      void unlistenProgress.then((unlisten) => unlisten());
    };
  }, []);

  const phase = isLaunchPhase(progress.phase) ? progress.phase : "checkingDocker";
  const statusText = t(`splash.phases.${phase}`);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6 py-12">
      <div className="w-full max-w-md text-center">
        <HeroGraphic size={200} className="mx-auto mb-8" />

        <p className="text-sm font-medium uppercase tracking-[0.25em] text-sky-300/80">
          {t("common.appName")}
        </p>
        <h1 className="mt-3 text-2xl font-semibold text-white">{t("splash.title")}</h1>
        <p className="mt-2 text-sm text-slate-400">{t("splash.subtitle")}</p>

        <div className="mt-10">
          <div className="mb-3 flex items-center justify-between text-sm">
            <span className="text-slate-300">{statusText}</span>
            <span className="font-mono text-sky-300">{progress.percent}%</span>
          </div>

          <div
            className="h-2 overflow-hidden rounded-full bg-white/10"
            role="progressbar"
            aria-valuenow={progress.percent}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={statusText}
          >
            <div
              className="h-full rounded-full bg-gradient-to-r from-[#bd34fe] to-[#41d1ff] transition-all duration-500 ease-out"
              style={{ width: `${Math.max(progress.percent, 2)}%` }}
            />
          </div>
        </div>

        <p className="mt-6 text-xs text-slate-500">{t("splash.hint")}</p>
      </div>
    </div>
  );
}
