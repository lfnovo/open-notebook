'use client'

import Link from 'next/link'
import Image from 'next/image'
import type { ChatImage } from '@/lib/types/api'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { X } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'

export function ChatImages({ images, onRemove, disabled, large = false, showProvenance = true }: {
  large?: boolean
  showProvenance?: boolean
  images: ChatImage[]
  onRemove?: (index: number) => void
  disabled?: boolean
}) {
  const { t } = useTranslation()
  return (
    <div className="flex flex-wrap gap-2">
      {images.map((image, index) => (
        <div key={`${index}-${image.name}`} className={`relative rounded-md border bg-muted p-1 ${large ? "w-full max-w-2xl" : ""}`}>
          <Dialog>
            <DialogTrigger asChild>
              <button type="button" className="block w-full rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                <Image src={image.data_url} alt={image.name} width={large ? 640 : 128} height={large ? 360 : 96}
                  unoptimized className={large ? "max-h-80 w-full object-contain" : "h-24 w-32 object-contain"} />
              </button>
            </DialogTrigger>
            <DialogContent className="max-w-4xl">
              <DialogTitle className="text-sm break-all">{image.name}</DialogTitle>
              <Image src={image.data_url} alt={image.name} width={1200} height={900}
                unoptimized className="max-h-[75vh] w-full object-contain" />
            </DialogContent>
          </Dialog>
          {showProvenance && image.kind === 'generated' && <p className={`text-xs text-muted-foreground ${large ? "" : "max-w-32"}`}>{t('chat.generatedImage')}</p>}
          {showProvenance && image.kind === 'source' && image.source_id && (
            <Link className={`block text-xs text-primary underline break-words ${large ? "" : "max-w-32"}`}
              href={`/sources/${encodeURIComponent(image.source_id)}`}>
              {t('chat.sourceImage', { source: image.source_title || image.source_id, page: image.page || 1 })}
            </Link>
          )}
          {onRemove && (
            <Button type="button" variant="secondary" size="icon" className="absolute -right-2 -top-2 h-6 w-6 rounded-full"
              aria-label={t('chat.removeImage', { name: image.name })} disabled={disabled} onClick={() => onRemove(index)}>
              <X className="h-3 w-3" />
            </Button>
          )}
        </div>
      ))}
    </div>
  )
}
