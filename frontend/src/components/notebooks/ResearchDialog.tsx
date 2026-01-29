'use client'

import React, { useState } from 'react'
import { Search, Download, BookOpen, FileText, Loader2, Check } from 'lucide-react'
import { toast } from 'sonner'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { searchAcmPapers, ingestAcmPaper, PaperResult } from '@/lib/api/agent'
import { Badge } from '@/components/ui/badge'

interface ResearchDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  notebookId: string
  onSuccess?: () => void
}

export function ResearchDialog({
  open,
  onOpenChange,
  notebookId,
  onSuccess
}: ResearchDialogProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<PaperResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [ingestingUrls, setIngestingUrls] = useState<Set<string>>(new Set())
  const [ingestedUrls, setIngestedUrls] = useState<Set<string>>(new Set())

  const handleSearch = async (e?: React.FormEvent) => {
    e?.preventDefault()
    if (!query.trim()) return

    setIsSearching(true)
    try {
      const response = await searchAcmPapers(query)
      setResults(response.results)
    } catch (error) {
      console.error('Search failed:', error)
      toast.error('Failed to search papers')
    } finally {
      setIsSearching(false)
    }
  }

  const handleIngest = async (paper: PaperResult) => {
    if (ingestingUrls.has(paper.pdf_url) || ingestedUrls.has(paper.pdf_url)) return

    setIngestingUrls(prev => new Set(prev).add(paper.pdf_url))
    try {
      await ingestAcmPaper({
        pdf_url: paper.pdf_url,
        notebook_id: notebookId,
        title: paper.title
      })
      
      setIngestedUrls(prev => new Set(prev).add(paper.pdf_url))
      toast.success('Paper added to notebook processing queue')
      onSuccess?.()
    } catch (error) {
      console.error('Ingest failed:', error)
      toast.error('Failed to add paper')
    } finally {
      setIngestingUrls(prev => {
        const next = new Set(prev)
        next.delete(paper.pdf_url)
        return next
      })
    }
  }

  const handleClose = () => {
    onOpenChange(false)
    // Optional: clear results on close?
    // setResults([])
    // setQuery('')
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[700px] h-[80vh] flex flex-col p-0 gap-0">
        <DialogHeader className="px-6 py-4 border-b">
          <DialogTitle className="flex items-center gap-2">
            <BookOpen className="h-5 w-5" />
            Research Papers (ACM)
          </DialogTitle>
          <DialogDescription>
            Search and add open access papers from ACM Digital Library directly to your notebook.
          </DialogDescription>
        </DialogHeader>

        <div className="p-4 border-b bg-muted/30">
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search for papers (e.g. 'Large Language Models')..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="pl-9"
                autoFocus
              />
            </div>
            <Button type="submit" disabled={isSearching || !query.trim()}>
              {isSearching ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Search'}
            </Button>
          </form>
        </div>

        <ScrollArea className="flex-1 p-4">
          {results.length === 0 && !isSearching ? (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground py-12">
              <BookOpen className="h-12 w-12 mb-4 opacity-20" />
              <p>Search for papers to get started</p>
            </div>
          ) : (
            <div className="space-y-4">
              {results.map((paper, index) => (
                <div 
                  key={`${paper.pdf_url}-${index}`}
                  className="flex flex-col gap-3 p-4 rounded-lg border bg-card hover:bg-accent/5 transition-colors"
                >
                  <div className="flex justify-between items-start gap-4">
                    <div className="space-y-1">
                      <h4 className="font-semibold leading-tight text-foreground">
                        {paper.title}
                      </h4>
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <FileText className="h-3 w-3" />
                          {paper.venue}
                        </span>
                        {paper.year && <span>• {paper.year}</span>}
                        {paper.citations !== undefined && <span>• {paper.citations} citations</span>}
                        <Badge variant="outline" className="text-xs font-normal h-5 px-1.5">
                          Open Access
                        </Badge>
                      </div>
                    </div>
                    
                    <Button
                      size="sm"
                      variant={ingestedUrls.has(paper.pdf_url) ? "secondary" : "default"}
                      disabled={ingestingUrls.has(paper.pdf_url) || ingestedUrls.has(paper.pdf_url)}
                      onClick={() => handleIngest(paper)}
                      className="shrink-0 min-w-[100px]"
                    >
                      {ingestingUrls.has(paper.pdf_url) ? (
                        <>
                          <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" />
                          Adding...
                        </>
                      ) : ingestedUrls.has(paper.pdf_url) ? (
                        <>
                          <Check className="h-3.5 w-3.5 mr-2" />
                          Added
                        </>
                      ) : (
                        <>
                          <Download className="h-3.5 w-3.5 mr-2" />
                          Add
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
        
        <div className="p-4 border-t bg-muted/10 text-xs text-center text-muted-foreground">
          Powered by OpenAlex & ACM • Showing top {results.length} results
        </div>
      </DialogContent>
    </Dialog>
  )
}
