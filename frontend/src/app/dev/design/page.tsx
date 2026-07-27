"use client"

// Living styleguide for the "Quiet Green" design foundation.
// Dev-only: returns 404 in production builds. Not translated on purpose —
// this is an internal spec artifact, not user-facing UI.

import { notFound } from "next/navigation"
import { useState } from "react"
import { Moon, Plus, Sun, Trash2, Search, Sparkles } from "lucide-react"

import { useTheme } from "@/lib/stores/theme-store"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { Separator } from "@/components/ui/separator"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Progress } from "@/components/ui/progress"
import { Checkbox } from "@/components/ui/checkbox"

const HUES = [
  ["fern", "acts — THE action green"],
  ["sage", "web / gathering"],
  ["gold", "notes & pdf"],
  ["teal", "AI / system voice"],
  ["plum", "video"],
  ["mauve", "audio"],
  ["slate", "paper / external"],
  ["violet", "derived insight"],
  ["clay", "warn / degraded"],
] as const

const TYPE_HUES = [
  "video",
  "pdf",
  "web",
  "audio",
  "paper",
  "note",
  "ai",
  "insight",
] as const

const CITE_CLASSES = ["source", "note", "derived", "external"] as const

const SURFACES = [
  ["--bg", "bg — app canvas"],
  ["--bg-deep", "bg-deep — rails, wells"],
  ["--surface", "surface — reading surface"],
  ["--surface-raised", "surface-raised — popovers, inputs"],
  ["--surface-recessed", "surface-recessed"],
  ["--surface-sunken", "surface-sunken — kbd, wells"],
] as const

const INKS = [
  ["--ink", "ink — primary text"],
  ["--ink-soft", "ink-soft — secondary"],
  ["--ink-faint", "ink-faint — metadata"],
  ["--ink-faintest", "ink-faintest — disabled"],
] as const

const SHADOWS = [
  ["--shadow-soft", "soft — panels, cards"],
  ["--shadow-lift", "lift — hover"],
  ["--shadow-pop", "pop — popovers own it"],
  ["--shadow-overlay", "overlay — modal sheets"],
] as const

const RADII = [
  ["--radius-sm", "sm 4px — chips, small buttons"],
  ["--radius-md", "md 5px — controls, inputs"],
  ["--radius-lg", "lg 5px — cards"],
  ["--radius-xl", "xl 6px — panels, overlays"],
] as const

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="font-display text-xl font-bold tracking-tight mt-10 mb-4">
      {children}
    </h2>
  )
}

function Swatch({ varName, label }: { varName: string; label: string }) {
  return (
    <div className="flex items-center gap-3">
      <div
        className="size-9 shrink-0 rounded-sm border"
        style={{ backgroundColor: `var(${varName})` }}
      />
      <div className="min-w-0">
        <div className="font-mono text-xs">{varName}</div>
        <div className="text-xs text-muted-foreground truncate">{label}</div>
      </div>
    </div>
  )
}

function Sheet() {
  const [progress] = useState(62)
  const { isDark, setTheme } = useTheme()

  return (
    <div className="bg-background text-foreground p-8">
      <header className="mb-2 flex items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold tracking-tight">
            Quiet Green — design foundation
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            fern acts · teal speaks · red destroys · warn is clay · color never
            washes a reading surface · popovers own the one real shadow
          </p>
        </div>
        <Button
          variant="outline"
          size="icon"
          aria-label="Toggle theme"
          onClick={() => setTheme(isDark ? "light" : "dark")}
        >
          {isDark ? <Sun /> : <Moon />}
        </Button>
      </header>

      <SectionTitle>Core palette</SectionTitle>
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        {HUES.map(([hue, note]) => (
          <div key={hue} className="flex items-center gap-2">
            <div
              className="size-9 shrink-0 rounded-sm border"
              style={{ backgroundColor: `var(--${hue})` }}
            />
            <div
              className="size-9 shrink-0 rounded-sm border"
              style={{ backgroundColor: `var(--${hue}-tint)` }}
            />
            <div className="min-w-0">
              <div className="font-mono text-xs">--{hue}</div>
              <div className="text-xs text-muted-foreground truncate">
                {note}
              </div>
            </div>
          </div>
        ))}
      </div>

      <SectionTitle>Surfaces &amp; ink</SectionTitle>
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        {SURFACES.map(([v, label]) => (
          <Swatch key={v} varName={v} label={label} />
        ))}
      </div>
      <div className="mt-4 space-y-1">
        {INKS.map(([v, label]) => (
          <div key={v} className="text-sm" style={{ color: `var(${v})` }}>
            The quick brown fox — <span className="font-mono text-xs">{label}</span>
          </div>
        ))}
      </div>

      <SectionTitle>Typography</SectionTitle>
      <div className="space-y-3">
        <div className="font-display text-2xl font-bold">
          Display — Bricolage Grotesque 700
        </div>
        <div className="text-sm">
          Body — Instrument Sans. Reading text stays on neutral surfaces;
          color is information, never decoration.
        </div>
        <div className="font-mono text-xs">
          Mono — Spline Sans Mono · for data, not prose · 128 chunks · 04:32
        </div>
      </div>

      <SectionTitle>Content-type hues (dots, ticks, chips — never washes)</SectionTitle>
      <div className="flex flex-wrap gap-2">
        {TYPE_HUES.map((t) => (
          <span
            key={t}
            className="inline-flex items-center gap-1.5 rounded-sm border bg-popover px-2 py-0.5 text-xs font-medium"
          >
            <span
              className="size-2 rounded-full"
              style={{ backgroundColor: `var(--type-${t})` }}
            />
            {t}
          </span>
        ))}
      </div>

      <SectionTitle>Evidence classes (citation chips)</SectionTitle>
      <div className="flex flex-wrap items-center gap-2">
        {CITE_CLASSES.map((c, i) => (
          <span
            key={c}
            className="inline-flex items-center gap-1.5 rounded-sm border bg-popover px-1.5 py-0.5 font-mono text-[10.5px]"
          >
            <span
              className="size-1.5 rounded-full"
              style={{ backgroundColor: `var(--cite-${c})` }}
            />
            {i + 1} · {c}
          </span>
        ))}
        <span className="inline-flex items-center gap-1.5 rounded-sm border border-dashed bg-transparent px-1.5 py-0.5 font-mono text-[10.5px] text-muted-foreground">
          ◦ synthesis
        </span>
      </div>
      <div className="mt-3 rounded-md border p-3 text-sm" style={{ backgroundColor: "var(--excerpt-wash)" }}>
        Cited passage sits on the one sanctioned tinted background —{" "}
        <mark className="rounded-[2px] px-0.5" style={{ backgroundColor: "var(--best-match)", color: "inherit" }}>
          the best-match sentence is a step stronger
        </mark>
        .
      </div>

      <SectionTitle>Context states (per-source inclusion)</SectionTitle>
      <div className="flex flex-wrap gap-2">
        <span className="inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 text-xs font-medium" style={{ backgroundColor: "var(--ctx-full-tint)", color: "var(--ctx-full)" }}>
          FULL
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 text-xs font-medium" style={{ backgroundColor: "var(--ctx-insights-tint)", color: "var(--ctx-insights)" }}>
          INSIGHTS
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 text-xs font-medium" style={{ backgroundColor: "var(--ctx-off-bg)", color: "var(--ctx-off-ink)" }}>
          OFF
        </span>
      </div>

      <SectionTitle>Radii &amp; shadows</SectionTitle>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {RADII.map(([v, label]) => (
          <div key={v} className="flex items-center gap-3">
            <div
              className="size-9 shrink-0 border bg-popover"
              style={{ borderRadius: `var(${v})` }}
            />
            <div className="text-xs text-muted-foreground">{label}</div>
          </div>
        ))}
      </div>
      <div className="mt-4 grid grid-cols-2 lg:grid-cols-4 gap-4">
        {SHADOWS.map(([v, label]) => (
          <div
            key={v}
            className="rounded-md border bg-card p-4 text-xs text-muted-foreground"
            style={{ boxShadow: `var(${v})` }}
          >
            {label}
          </div>
        ))}
      </div>

      <SectionTitle>Buttons</SectionTitle>
      <div className="flex flex-wrap items-center gap-3">
        <Button>
          <Plus /> New source
        </Button>
        <Button variant="secondary">Secondary</Button>
        <Button variant="outline">Outline</Button>
        <Button variant="ghost">Ghost</Button>
        <Button variant="link">Link</Button>
        <Button variant="destructive">
          <Trash2 /> Delete
        </Button>
        <Button disabled>Disabled</Button>
        <Button size="sm">Small</Button>
        <Button size="icon" aria-label="Search">
          <Search />
        </Button>
      </div>

      <SectionTitle>Badges</SectionTitle>
      <div className="flex flex-wrap items-center gap-2">
        <Badge>Default</Badge>
        <Badge variant="secondary">Secondary</Badge>
        <Badge variant="outline">Outline</Badge>
        <Badge variant="destructive">Failed</Badge>
        <Badge variant="secondary">
          <span className="size-2 rounded-full" style={{ backgroundColor: "var(--type-pdf)" }} />
          PDF
        </Badge>
        <Badge variant="secondary">
          <Sparkles className="text-teal" /> AI
        </Badge>
      </div>

      <SectionTitle>Card</SectionTitle>
      <div className="grid gap-4 lg:grid-cols-2 max-w-3xl">
        <Card>
          <CardHeader>
            <CardTitle>Attention is all you need</CardTitle>
            <CardDescription>
              Hairline border, no default shadow — surfaces separate with
              lines, not depth.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm">
            The dominant sequence transduction models are based on complex
            recurrent or convolutional neural networks.
          </CardContent>
          <CardFooter className="gap-2">
            <Button size="sm" variant="outline">
              Open
            </Button>
            <Button size="sm" variant="ghost">
              Save as note
            </Button>
          </CardFooter>
        </Card>
        <Card className="card-hover">
          <CardHeader>
            <CardTitle>Hover me</CardTitle>
            <CardDescription>card-hover raises the surface.</CardDescription>
          </CardHeader>
        </Card>
      </div>

      <SectionTitle>Tabs</SectionTitle>
      <Tabs defaultValue="content" className="max-w-md">
        <TabsList>
          <TabsTrigger value="content">Content</TabsTrigger>
          <TabsTrigger value="insights">Insights</TabsTrigger>
          <TabsTrigger value="chat">Chat</TabsTrigger>
        </TabsList>
        <TabsContent value="content" className="pt-3 text-sm text-muted-foreground">
          Underline tabs — the active one carries a fern spine.
        </TabsContent>
        <TabsContent value="insights" className="pt-3 text-sm text-muted-foreground">
          Insights speak with the teal voice.
        </TabsContent>
        <TabsContent value="chat" className="pt-3 text-sm text-muted-foreground">
          Chat content.
        </TabsContent>
      </Tabs>

      <SectionTitle>Forms</SectionTitle>
      <div className="max-w-md space-y-4">
        <div className="space-y-2">
          <Label htmlFor={`name-input`}>Notebook name</Label>
          <Input id="name-input" placeholder="e.g. Transformer papers" />
        </div>
        <div className="space-y-2">
          <Label>Model</Label>
          <Select>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Pick a model" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="a">claude-sonnet-5</SelectItem>
              <SelectItem value="b">gpt-5.2</SelectItem>
              <SelectItem value="c">gemini-3-flash</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Textarea placeholder="Describe what you want to research…" />
        <div className="flex items-center gap-6">
          <label className="flex items-center gap-2 text-sm">
            <Checkbox defaultChecked /> Include insights
          </label>
          <label className="flex items-center gap-2 text-sm">
            <Checkbox /> Auto-embed
          </label>
        </div>
        <Progress value={progress} />
      </div>

      <SectionTitle>Overlays</SectionTitle>
      <div className="flex flex-wrap items-center gap-3">
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline">Open dialog</Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Rename notebook</DialogTitle>
              <DialogDescription>
                Overlays use the one real shadow and 6px corners.
              </DialogDescription>
            </DialogHeader>
            <Input placeholder="Notebook name" />
            <DialogFooter>
              <Button variant="ghost">Cancel</Button>
              <Button>Save</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline">Dropdown</Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuLabel>Source</DropdownMenuLabel>
            <DropdownMenuItem>Open</DropdownMenuItem>
            <DropdownMenuItem>Save as note</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive">Delete</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <Popover>
          <PopoverTrigger asChild>
            <Button variant="outline">Popover</Button>
          </PopoverTrigger>
          <PopoverContent className="text-sm">
            Popovers own the pop shadow.
          </PopoverContent>
        </Popover>

        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost">Tooltip</Button>
          </TooltipTrigger>
          <TooltipContent>Quiet ink tooltip</TooltipContent>
        </Tooltip>
      </div>

      <SectionTitle>Feedback</SectionTitle>
      <div className="max-w-xl space-y-3">
        <Alert>
          <Sparkles className="size-4" />
          <AlertTitle>Embedding complete</AlertTitle>
          <AlertDescription>
            All 128 chunks are searchable now.
          </AlertDescription>
        </Alert>
        <Alert variant="destructive">
          <Trash2 className="size-4" />
          <AlertTitle>Processing failed</AlertTitle>
          <AlertDescription>
            Red only ever means destructive or broken.
          </AlertDescription>
        </Alert>
      </div>

      <Separator className="my-10" />
      <p className="text-xs text-muted-foreground">
        Canonical tokens: <span className="font-mono">frontend/src/app/globals.css</span> ·
        laws &amp; component inventory: design foundation doc.
      </p>
    </div>
  )
}

// Dark overrides only redefine raw tokens; aliases (e.g. --popover:
// var(--surface-raised)) resolve where they are DECLARED (:root = <html>),
// so themes only switch correctly via the `dark` class on the document root —
// a nested `.dark` wrapper inherits already-resolved light values. Hence one
// theme at a time here, toggled through the app's real theme store.
export default function DesignPage() {
  if (process.env.NODE_ENV === "production") {
    notFound()
  }

  return (
    <div className="min-h-screen">
      <Sheet />
    </div>
  )
}
