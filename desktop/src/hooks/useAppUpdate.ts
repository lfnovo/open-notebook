import { useCallback, useEffect, useRef, useState } from "react";
import { check, type Update } from "@tauri-apps/plugin-updater";
import { relaunch } from "@tauri-apps/plugin-process";
import { api } from "../lib/api";
import type { InstallContext, UpdateInfo } from "../types";

const AUTO_CHECK_DELAY_MS = 8000;

let pendingUpdate: Update | null = null;

export function useAppUpdate() {
  const [installContext, setInstallContext] = useState<InstallContext | null>(null);
  const [updateInfo, setUpdateInfo] = useState<UpdateInfo>({
    status: "idle",
    currentVersion: "0.0.0",
  });
  const autoCheckStarted = useRef(false);

  const loadContext = useCallback(async () => {
    const context = await api.getInstallContext();
    setInstallContext(context);
    setUpdateInfo((prev) => ({
      ...prev,
      currentVersion: context.currentVersion,
      status: context.isDevelopment ? "unsupported" : prev.status,
    }));
    return context;
  }, []);

  const checkNow = useCallback(async () => {
    const context = installContext ?? (await loadContext());

    if (context.isDevelopment) {
      setUpdateInfo((prev) => ({ ...prev, status: "unsupported", dismissed: false }));
      return;
    }

    setUpdateInfo((prev) => ({
      ...prev,
      status: "checking",
      error: undefined,
      dismissed: false,
    }));

    try {
      const update = await check();
      if (!update) {
        pendingUpdate = null;
        setUpdateInfo((prev) => ({
          ...prev,
          status: "uptodate",
          latestVersion: undefined,
          notes: undefined,
        }));
        return;
      }

      pendingUpdate = update;

      if (!context.canSelfUpdate) {
        setUpdateInfo((prev) => ({
          ...prev,
          status: "managed",
          latestVersion: update.version,
          notes: update.body ?? undefined,
        }));
        return;
      }

      setUpdateInfo((prev) => ({
        ...prev,
        status: "available",
        latestVersion: update.version,
        notes: update.body ?? undefined,
      }));
    } catch (error) {
      pendingUpdate = null;
      setUpdateInfo((prev) => ({
        ...prev,
        status: "error",
        error: String(error),
      }));
    }
  }, [installContext, loadContext]);

  const installAndRestart = useCallback(async () => {
    if (!pendingUpdate) {
      setUpdateInfo((prev) => ({
        ...prev,
        status: "error",
        error: "No pending update",
      }));
      return;
    }

    setUpdateInfo((prev) => ({
      ...prev,
      status: "downloading",
      progress: 0,
      error: undefined,
    }));

    try {
      let downloaded = 0;
      let total = 0;

      await pendingUpdate.downloadAndInstall((event) => {
        if (event.event === "Started") {
          total = event.data.contentLength ?? 0;
        }
        if (event.event === "Progress") {
          downloaded += event.data.chunkLength;
          const progress = total > 0 ? Math.round((downloaded / total) * 100) : undefined;
          setUpdateInfo((prev) => ({
            ...prev,
            status: "downloading",
            progress,
          }));
        }
      });

      setUpdateInfo((prev) => ({ ...prev, status: "ready_restart", progress: 100 }));
      await relaunch();
    } catch (error) {
      setUpdateInfo((prev) => ({
        ...prev,
        status: "error",
        error: String(error),
      }));
    }
  }, []);

  const dismiss = useCallback(() => {
    setUpdateInfo((prev) => ({ ...prev, dismissed: true }));
  }, []);

  const openReleasePage = useCallback(async () => {
    await api.openReleasePage();
  }, []);

  useEffect(() => {
    void loadContext();
  }, [loadContext]);

  useEffect(() => {
    if (autoCheckStarted.current) return;
    autoCheckStarted.current = true;

    const timer = window.setTimeout(() => {
      void checkNow();
    }, AUTO_CHECK_DELAY_MS);

    return () => window.clearTimeout(timer);
  }, [checkNow]);

  const showBanner =
    !updateInfo.dismissed &&
    (updateInfo.status === "available" || updateInfo.status === "managed");

  return {
    installContext,
    updateInfo,
    showBanner,
    checkNow,
    installAndRestart,
    dismiss,
    openReleasePage,
  };
}
