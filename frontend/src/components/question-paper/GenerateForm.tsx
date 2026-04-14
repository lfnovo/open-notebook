'use client'

import { useState } from 'react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Info, X, Plus } from 'lucide-react'
import { BookUploader } from './BookUploader'
import type { GeneratePaperRequest, QuestionDifficulty } from '@/lib/types/question-paper'

interface GenerateFormProps {
  onSubmit: (request: GeneratePaperRequest) => void
  isLoading: boolean
}

const DEFAULT_SECTION_CONFIG: Record<string, number> = { mcq: 10, short: 5, scenario: 3 }
const QUESTION_TYPES = ['mcq', 'short', 'scenario', 'calculation', 'definition']

const SECTION_DESCRIPTIONS: Record<string, string> = {
  mcq: 'Multiple-choice questions with 4 options (A–D). One correct answer. Best for testing recall and recognition quickly.',
  short: 'Short-answer questions requiring a 1–3 sentence written response. Tests understanding, not just memorisation.',
  scenario: 'Case-study style questions that present a real-world situation and ask the student to apply knowledge to solve it.',
  calculation: 'Numerical or formula-based questions where the student must show working and arrive at a specific figure.',
  definition: 'Ask the student to define a term or concept in their own words. Good for testing vocabulary and foundational knowledge.',
}

// Small inline info button with a tooltip
function FieldInfo({ children }: { children: React.ReactNode }) {
  return (
    <TooltipProvider delayDuration={100}>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            className="inline-flex items-center justify-center rounded-full text-muted-foreground hover:text-foreground transition-colors focus:outline-none"
            aria-label="More information"
          >
            <Info className="h-3.5 w-3.5" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="right" className="max-w-xs text-sm leading-relaxed">
          {children}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

function FieldLabel({ htmlFor, label, children }: { htmlFor?: string; label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-1.5">
      <Label htmlFor={htmlFor}>{label}</Label>
      <FieldInfo>{children}</FieldInfo>
    </div>
  )
}

export function GenerateForm({ onSubmit, isLoading }: GenerateFormProps) {
  const { t } = useTranslation()
  const [topic, setTopic] = useState('')
  const [difficulty, setDifficulty] = useState<QuestionDifficulty>('medium')
  const [targetMarks, setTargetMarks] = useState(50)
  const [sectionConfig, setSectionConfig] = useState<Record<string, number>>(DEFAULT_SECTION_CONFIG)
  const [newSectionType, setNewSectionType] = useState('')
  const [newSectionCount, setNewSectionCount] = useState(5)
  const [objectivesText, setObjectivesText] = useState('')
  const [bookId, setBookId] = useState<string | null>(null)
  const [selectedChapters, setSelectedChapters] = useState<number[] | null>(null)
  const [autoTopic, setAutoTopic] = useState<string>('')  // derived from book when no manual topic

  const handleAddSection = () => {
    const type = newSectionType.trim().toLowerCase()
    if (!type) return
    setSectionConfig((prev) => ({ ...prev, [type]: newSectionCount }))
    setNewSectionType('')
    setNewSectionCount(5)
  }

  const handleRemoveSection = (key: string) => {
    setSectionConfig((prev) => {
      const next = { ...prev }
      delete next[key]
      return next
    })
  }

  const handleUpdateSectionCount = (key: string, value: string) => {
    const n = parseInt(value, 10)
    if (!isNaN(n) && n > 0) {
      setSectionConfig((prev) => ({ ...prev, [key]: n }))
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const effectiveTopic = topic.trim() || autoTopic
    if (!effectiveTopic) return
    if (Object.keys(sectionConfig).length === 0) return

    const objectives = objectivesText
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean)

    onSubmit({
      topic: effectiveTopic,
      difficulty,
      target_marks: targetMarks,
      section_config: sectionConfig,
      curriculum_objectives: objectives,
      generator_model: null,
      reviewer_model: null,
      book_id: bookId,
      selected_chapters: selectedChapters,
    })
  }

  const totalQuestions = Object.values(sectionConfig).reduce((a, b) => a + b, 0)

  return (
    <form onSubmit={handleSubmit} className="space-y-6">

      {/* ── Topic — hidden when book is loaded (auto-derived from book/chapters) ── */}
      {!bookId && (
        <div className="space-y-2">
          <FieldLabel htmlFor="topic" label="Topic">
            <p>The subject the entire paper will be about. Be specific — the more focused the topic, the better the questions.</p>
            <p className="mt-1 text-muted-foreground">
              <span className="font-medium text-foreground">Examples:</span><br />
              • "Mutual Funds — NFO Basics"<br />
              • "Chapter 3: The Water Cycle"<br />
              • "Python List Comprehensions"
            </p>
          </FieldLabel>
          <Input
            id="topic"
            placeholder="e.g., Mutual Funds — NFO Basics"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            required={!bookId}
          />
        </div>
      )}

      {/* ── Difficulty + Target Marks ── */}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <FieldLabel label="Difficulty">
            <p>Controls how hard the questions are overall.</p>
            <ul className="mt-1 space-y-1 text-muted-foreground">
              <li><span className="font-medium text-foreground">Easy</span> — recall and basic definitions. Suitable for beginners or a warm-up quiz.</li>
              <li><span className="font-medium text-foreground">Medium</span> — mix of recall and application. Good for mid-term tests.</li>
              <li><span className="font-medium text-foreground">Hard</span> — analysis, edge cases, and multi-step reasoning. For advanced students or finals.</li>
            </ul>
          </FieldLabel>
          <Select value={difficulty} onValueChange={(v) => setDifficulty(v as QuestionDifficulty)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="easy">Easy</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="hard">Hard</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <FieldLabel htmlFor="marks" label="Total Marks">
            <p>The maximum score a student can get on this paper.</p>
            <p className="mt-1 text-muted-foreground">The AI distributes marks across questions based on type and difficulty. A 50-mark paper might give 1 mark per MCQ and 5 marks per scenario question.</p>
            <p className="mt-1 text-muted-foreground"><span className="font-medium text-foreground">Example:</span> 50 for a class test, 100 for a final exam.</p>
          </FieldLabel>
          <Input
            id="marks"
            type="number"
            min={5}
            max={500}
            value={targetMarks}
            onChange={(e) => setTargetMarks(parseInt(e.target.value, 10) || 50)}
          />
        </div>
      </div>

      {/* ── Sections ── */}
      <div className="space-y-2">
        <FieldLabel label="Sections">
          <p>Defines <span className="font-medium text-foreground">what types of questions</span> appear and <span className="font-medium text-foreground">how many</span> of each.</p>
          <div className="mt-2 space-y-1.5 text-muted-foreground">
            {Object.entries(SECTION_DESCRIPTIONS).map(([type, desc]) => (
              <p key={type}><span className="font-medium text-foreground capitalize">{type}</span> — {desc}</p>
            ))}
          </div>
          <p className="mt-2 text-muted-foreground"><span className="font-medium text-foreground">Example:</span> 10 MCQ + 5 Short + 3 Scenario = 18 questions total.</p>
        </FieldLabel>

        <p className="text-xs text-muted-foreground">
          {totalQuestions} question{totalQuestions !== 1 ? 's' : ''} total across {Object.keys(sectionConfig).length} section{Object.keys(sectionConfig).length !== 1 ? 's' : ''}
        </p>

        <div className="space-y-2">
          {Object.entries(sectionConfig).map(([key, count]) => (
            <div key={key} className="flex items-center gap-2">
              <TooltipProvider delayDuration={100}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Badge variant="secondary" className="min-w-24 justify-center capitalize cursor-help">
                      {key}
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent side="right" className="max-w-xs text-sm">
                    {SECTION_DESCRIPTIONS[key] ?? `Custom question type: "${key}"`}
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              <Input
                type="number"
                min={1}
                max={50}
                value={count}
                onChange={(e) => handleUpdateSectionCount(key, e.target.value)}
                className="w-20"
              />
              <span className="text-sm text-muted-foreground">questions</span>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => handleRemoveSection(key)}
                className="h-8 w-8 shrink-0"
              >
                <X className="h-3 w-3" />
              </Button>
            </div>
          ))}
        </div>

        {/* Add section row */}
        <div className="flex gap-2 mt-2">
          <Select value={newSectionType} onValueChange={setNewSectionType}>
            <SelectTrigger className="flex-1">
              <SelectValue placeholder="Add a question type..." />
            </SelectTrigger>
            <SelectContent>
              {QUESTION_TYPES.filter((type) => !(type in sectionConfig)).map((type) => (
                <SelectItem key={type} value={type}>
                  <span className="capitalize font-medium">{type}</span>
                  <span className="text-muted-foreground ml-2 text-xs">
                    — {SECTION_DESCRIPTIONS[type]?.split('.')[0]}
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            type="number"
            min={1}
            max={50}
            value={newSectionCount}
            onChange={(e) => setNewSectionCount(parseInt(e.target.value, 10) || 5)}
            className="w-20"
          />
          <Button
            type="button"
            variant="outline"
            size="icon"
            onClick={handleAddSection}
            disabled={!newSectionType}
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* ── Curriculum Objectives ── */}
      <div className="space-y-2">
        <FieldLabel htmlFor="objectives" label="Curriculum Objectives (optional)">
          <p>A list of learning goals this paper should cover — one per line.</p>
          <p className="mt-1 text-muted-foreground">After generation, the AI checks which objectives are covered by the questions and flags any gaps. This helps a teacher spot what's missing before handing out the paper.</p>
          <p className="mt-1 text-muted-foreground"><span className="font-medium text-foreground">Leave blank</span> if you don't have a syllabus — the AI will still generate good questions, just without the coverage report.</p>
          <p className="mt-1 text-muted-foreground">
            <span className="font-medium text-foreground">Example:</span><br />
            • Understand what an NFO is<br />
            • Explain the subscription process<br />
            • Compare open-ended and close-ended funds
          </p>
        </FieldLabel>
        <Textarea
          id="objectives"
          placeholder={"Understand what an NFO is\nExplain the subscription process\nCompare open-ended and close-ended funds"}
          value={objectivesText}
          onChange={(e) => setObjectivesText(e.target.value)}
          rows={4}
        />
      </div>

      {/* ── Book / PDF upload ── */}
      <div className="space-y-2">
        <Separator />
        <FieldLabel label="Book / PDF Source (optional)">
          <p>Upload a book, PDF, or document if you want questions to come <span className="font-medium text-foreground">only from that material</span> — not from the AI's general knowledge.</p>
          <p className="mt-1 text-muted-foreground">After upload, the AI detects chapters or sections inside the file. You can then pick which chapters to include — useful if you only want questions from Chapter 4 of a textbook, for example.</p>
          <div className="mt-1 space-y-0.5 text-muted-foreground">
            <p><span className="font-medium text-foreground">Supported:</span> PDF, EPUB, DOCX, TXT, Markdown</p>
            <p><span className="font-medium text-foreground">Skip this</span> if you just want the AI to generate questions from its own knowledge about the topic.</p>
          </div>
        </FieldLabel>

        <BookUploader
          onBookReady={(id, chapters, bookTitle, chapterTitles) => {
            setBookId(id)
            setSelectedChapters(chapters)
            // Auto-fill topic: use book title if all chapters, or first 2 chapter titles if subset
            const derived = chapterTitles.length === 0
              ? bookTitle
              : chapterTitles.length <= 2
                ? chapterTitles.join(' & ')
                : bookTitle
            setAutoTopic(derived)
          }}
          onClear={() => {
            setBookId(null)
            setSelectedChapters(null)
            setAutoTopic('')
          }}
        />

        {bookId && (
          <p className="text-xs text-primary font-medium">
            ✓ Questions will be grounded in the uploaded book content
          </p>
        )}
      </div>

      <Button
        type="submit"
        className="w-full"
        disabled={isLoading || (!topic.trim() && !autoTopic) || Object.keys(sectionConfig).length === 0}
      >
        {isLoading ? 'Generating...' : 'Generate Paper'}
      </Button>
    </form>
  )
}
