"use client"

import { useTranslation } from "@/lib/hooks/use-translation"
import { useDiscoverLinks } from "@/lib/hooks/use-sources"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { FormSection } from "@/components/ui/form-section"
import { LoaderIcon } from "lucide-react"

interface SelectLinksStepProps {
  sourceUrl: string
  selectedLinks: string[]
  onSelectedChange: (urls: string[]) => void
  onSkip: () => void
}

export function SelectLinksStep({
  sourceUrl,
  selectedLinks,
  onSelectedChange,
  onSkip,
}: SelectLinksStepProps) {
  const { t } = useTranslation()
  const { data, isLoading, isError } = useDiscoverLinks(sourceUrl, true)

  const links = data?.links ?? []

  const toggle = (url: string) => {
    if (selectedLinks.includes(url)) {
      onSelectedChange(selectedLinks.filter((u) => u !== url))
    } else {
      onSelectedChange([...selectedLinks, url])
    }
  }

  const selectAll = () => onSelectedChange(links.map((l) => l.url))
  const selectNone = () => onSelectedChange([])
  const selectSameDomain = () =>
    onSelectedChange(links.filter((l) => l.same_domain).map((l) => l.url))

  if (isLoading) {
    return (
      <div className="flex items-center gap-3 py-8">
        <LoaderIcon className="h-5 w-5 animate-spin text-primary" />
        <span className="text-sm text-muted-foreground">{t("sources.scanningLinks")}</span>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="space-y-3 py-6">
        <p className="text-sm text-destructive">{t("sources.discoverLinksError")}</p>
        <Button type="button" variant="outline" onClick={onSkip}>
          {t("sources.skipImportOriginal")}
        </Button>
      </div>
    )
  }

  if (links.length === 0) {
    return (
      <div className="space-y-3 py-6">
        <p className="text-sm text-muted-foreground">{t("sources.noLinksFound")}</p>
      </div>
    )
  }

  return (
    <FormSection
      title={t("sources.selectLinks")}
      description={t("sources.selectLinksDescription")}
    >
      <div className="flex items-center justify-between mb-3">
        <Badge variant="secondary">
          {t("sources.linksFound").replace("{count}", links.length.toString())}
        </Badge>
        <div className="flex gap-2">
          <Button type="button" variant="ghost" size="sm" onClick={selectAll}>
            {t("sources.selectAll")}
          </Button>
          <Button type="button" variant="ghost" size="sm" onClick={selectSameDomain}>
            {t("sources.selectSameDomain")}
          </Button>
          <Button type="button" variant="ghost" size="sm" onClick={selectNone}>
            {t("sources.selectNone")}
          </Button>
        </div>
      </div>

      <ul className="space-y-2 max-h-72 overflow-y-auto">
        {links.map((link) => (
          <li key={link.url} className="flex items-start gap-3 rounded-md border p-2">
            <Checkbox
              checked={selectedLinks.includes(link.url)}
              onCheckedChange={() => toggle(link.url)}
              className="mt-1"
            />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium truncate">{link.text || link.url}</span>
                <Badge variant={link.same_domain ? "secondary" : "outline"} className="shrink-0">
                  {link.same_domain ? t("sources.sameDomainBadge") : t("sources.externalBadge")}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground truncate">{link.url}</p>
            </div>
          </li>
        ))}
      </ul>
    </FormSection>
  )
}
