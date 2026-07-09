import type { ReactNode } from "react";
import { useI18n } from "../i18n";

interface ShellProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  actions?: ReactNode;
}

export function ScreenShell({ title, subtitle, children, actions }: ShellProps) {
  const { t } = useI18n();

  return (
    <div className="mx-auto flex min-h-screen max-w-4xl flex-col px-6 py-8">
      <header className="mb-8 flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-sky-300/80">
            {t("common.appName")}
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-white">{title}</h1>
          {subtitle ? <p className="mt-2 max-w-2xl text-slate-300">{subtitle}</p> : null}
        </div>
        {actions}
      </header>
      <main className="flex-1">{children}</main>
    </div>
  );
}

interface CardProps {
  children: ReactNode;
  className?: string;
}

export function Card({ children, className = "" }: CardProps) {
  return (
    <div
      className={`rounded-2xl border border-white/10 bg-white/5 p-6 shadow-xl backdrop-blur ${className}`}
    >
      {children}
    </div>
  );
}

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger";
}

export function Button({ variant = "primary", className = "", ...props }: ButtonProps) {
  const variants = {
    primary: "bg-sky-500 hover:bg-sky-400 text-white",
    secondary: "bg-white/10 hover:bg-white/15 text-white",
    danger: "bg-rose-600 hover:bg-rose-500 text-white",
  };

  return (
    <button
      className={`rounded-xl px-4 py-2.5 text-sm font-medium transition ${variants[variant]} ${className}`}
      {...props}
    />
  );
}

export function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${
        ok ? "bg-emerald-500/15 text-emerald-300" : "bg-amber-500/15 text-amber-200"
      }`}
    >
      {label}
    </span>
  );
}

export function ChecklistItem({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-center gap-3 text-sm">
      <span
        className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
          ok ? "bg-emerald-500/20 text-emerald-300" : "bg-white/10 text-slate-400"
        }`}
      >
        {ok ? "✓" : "○"}
      </span>
      <span className={ok ? "text-slate-200" : "text-slate-400"}>{label}</span>
    </div>
  );
}

interface GuidanceCardProps {
  ready?: boolean;
  stepLabel?: string;
  headline: string;
  description: string;
  hint?: string;
  children?: ReactNode;
}

export function GuidanceCard({
  ready = false,
  stepLabel,
  headline,
  description,
  hint,
  children,
}: GuidanceCardProps) {
  return (
    <Card
      className={`space-y-4 ${
        ready
          ? "border-emerald-400/30 bg-emerald-500/10"
          : "border-sky-400/20 bg-sky-500/5"
      }`}
    >
      {stepLabel ? (
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-300/80">
          {stepLabel}
        </p>
      ) : null}
      <div>
        <h2 className={`text-xl font-semibold ${ready ? "text-emerald-200" : "text-white"}`}>
          {headline}
        </h2>
        <p className="mt-2 text-slate-300">{description}</p>
        {hint ? <p className="mt-3 text-sm text-slate-400">{hint}</p> : null}
      </div>
      {children}
    </Card>
  );
}
