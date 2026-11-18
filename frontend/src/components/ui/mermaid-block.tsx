'use client'

import { useEffect, useId, useRef, useState, type ReactNode } from 'react'

import { Button } from '@/components/ui/button'
import { useTranslation } from '@/lib/hooks/use-translation'

// While an answer streams in, the source changes on every token. Wait for it
// to settle before parsing so partial syntax never triggers a render.
export const SETTLE_DELAY_MS = 300

// A diagram can carry its own %%{init}%% directive. Mermaid only protects the
// keys listed here from it, so list every option this component relies on.
const SECURE_KEYS = [
  'secure',
  'securityLevel',
  'startOnLoad',
  'maxTextSize',
  'suppressErrorRendering',
  'maxEdges',
  'htmlLabels',
  'themeCSS',
  'theme',
]

// Mermaid sizes the SVG to width="100%" with a max-width, which shrinks a wide
// diagram until its text is unreadable. Pin it to its natural width instead so
// the container scrolls. Only the root <svg> tag is edited, and an SVG without a
// recognisable viewBox is left as is.
function withNaturalWidth(svg: string): string {
  const rootTag = /<svg\b[^>]*>/.exec(svg)?.[0]
  const viewBoxWidth = rootTag && /viewBox="[-\d.]+ [-\d.]+ ([\d.]+) [\d.]+"/.exec(rootTag)?.[1]
  if (!rootTag || !viewBoxWidth) {
    return svg
  }
  const pinnedTag = rootTag
    .replace(' width="100%"', ` width="${viewBoxWidth}"`)
    .replace(/max-width:\s*[\d.]+px;?/, '')
  return svg.replace(rootTag, pinnedTag)
}

type RenderState = { status: 'pending' } | { status: 'ready'; svg: string } | { status: 'failed' }

interface MermaidBlockProps {
  source: string
  isDark: boolean
  // The regular code block, used as the fallback and for the "show code" view.
  codeBlock: ReactNode
}

export function MermaidBlock({ source, isDark, codeBlock }: MermaidBlockProps) {
  const { t } = useTranslation()
  const [state, setState] = useState<RenderState>({ status: 'pending' })
  const [showCode, setShowCode] = useState(false)
  const diagramId = `mermaid-${useId().replace(/:/g, '')}`
  const attempts = useRef(0)

  useEffect(() => {
    let cancelled = false

    const timer = setTimeout(async () => {
      // Mermaid removes any element that already has the id it is given, and the
      // diagram on screen holds the previous id, so every attempt needs its own.
      const renderId = `${diagramId}-${++attempts.current}`
      try {
        // Loaded on demand so the library stays out of the main bundle.
        const { default: mermaid } = await import('mermaid')
        mermaid.initialize({
          startOnLoad: false,
          // The source is model output: no HTML labels, click handlers or links.
          // 'strict' alone still lets sanitised HTML such as <img src=...> through.
          securityLevel: 'strict',
          htmlLabels: false,
          suppressErrorRendering: true,
          secure: SECURE_KEYS,
          theme: isDark ? 'dark' : 'default',
        })
        if (!(await mermaid.parse(source, { suppressErrors: true }))) {
          if (!cancelled) setState({ status: 'failed' })
          return
        }
        const { svg } = await mermaid.render(renderId, source)
        if (!cancelled) setState({ status: 'ready', svg: withNaturalWidth(svg) })
      } catch {
        document.getElementById(`d${renderId}`)?.remove()
        if (!cancelled) setState({ status: 'failed' })
      }
    }, SETTLE_DELAY_MS)

    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [source, isDark, diagramId])

  if (state.status !== 'ready') {
    return <>{codeBlock}</>
  }

  return (
    <div className="my-4">
      <div className="mb-1 flex justify-end">
        <Button type="button" variant="ghost" size="sm" className="text-muted-foreground" onClick={() => setShowCode((value) => !value)}>
          {showCode ? t('common.showDiagram') : t('common.showCode')}
        </Button>
      </div>
      {showCode ? (
        codeBlock
      ) : (
        <div
          className="overflow-x-auto rounded-md border border-border p-4 [&_svg]:mx-auto [&_svg]:h-auto"
          data-testid="mermaid-diagram"
          dangerouslySetInnerHTML={{ __html: state.svg }}
        />
      )}
    </div>
  )
}
