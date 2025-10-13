import { useEffect, useMemo, useRef, useState } from 'react';
import { FileText, Loader2, PenSquare, Sparkles } from 'lucide-react';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
} from '@/components/ui/select';
import builtinTemplatesRaw from '@/components/notebook/templates/builtin-templates';
import { apiClient } from '@/lib/api-client';
import type { Note, ResearchResponse } from '@/types/api';

type TemplateScope = 'builtin' | 'custom';

type ReportTemplate = {
  id: string;
  name: string;
  description: string | null;
  body_md: string;
  scope: TemplateScope;
  created_at?: string;
};

const CUSTOM_TEMPLATE_KEY = 'custom:adhoc';
const CUSTOM_TEMPLATE_STORAGE_KEY = 'open-notebook:report-templates';

const builtInTemplates: ReportTemplate[] = builtinTemplatesRaw.map((template) => ({
  ...template,
  scope: 'builtin' as const,
  created_at: undefined,
}));

const loadCustomTemplates = (): ReportTemplate[] => {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(CUSTOM_TEMPLATE_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((item) => ({
        id: typeof item.id === 'string' ? item.id : `custom:${crypto.randomUUID?.() ?? Date.now()}`,
        name: typeof item.name === 'string' ? item.name : 'Custom Template',
        description: typeof item.description === 'string' ? item.description : null,
        body_md: typeof item.body_md === 'string' ? item.body_md : '',
        scope: 'custom' as const,
        created_at: typeof item.created_at === 'string' ? item.created_at : new Date().toISOString(),
      }))
      .filter((item) => item.body_md.trim().length > 0);
  } catch (error) {
    console.error('Failed to load custom templates from storage:', error);
    return [];
  }
};

const persistCustomTemplates = (templates: ReportTemplate[]) => {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(
      CUSTOM_TEMPLATE_STORAGE_KEY,
      JSON.stringify(
        templates.map((template) => ({
          ...template,
          scope: 'custom',
        })),
      ),
    );
  } catch (error) {
    console.error('Failed to persist custom templates:', error);
  }
};

const resolveTemplateByKey = (key: string, builtins: ReportTemplate[], custom: ReportTemplate[]): ReportTemplate | null => {
  if (key === CUSTOM_TEMPLATE_KEY) return null;
  const all = [...builtins, ...custom];
  return all.find((template) => template.id === key) ?? null;
};

interface GenerateReportDialogProps {
  open: boolean;
  notebookId: string;
  onOpenChange: (open: boolean) => void;
  onReportCreated: (payload: { note: Note; research: ResearchResponse }) => void;
}

const GenerateReportDialog = ({
  open,
  notebookId,
  onOpenChange,
  onReportCreated,
}: GenerateReportDialogProps) => {
  const builtinTemplatesState = builtInTemplates;
  const [customTemplates, setCustomTemplates] = useState<ReportTemplate[]>([]);

  const initialTemplate = builtinTemplatesState[0] ?? null;

  const [selectedTemplateKey, setSelectedTemplateKey] = useState<string>(
    initialTemplate?.id ?? CUSTOM_TEMPLATE_KEY,
  );
  const [templateBody, setTemplateBody] = useState<string>(initialTemplate?.body_md ?? '');
  const [hasEditedTemplate, setHasEditedTemplate] = useState(false);

  const [showSaveTemplate, setShowSaveTemplate] = useState(false);
  const [newTemplateName, setNewTemplateName] = useState('');
  const [newTemplateDescription, setNewTemplateDescription] = useState('');

  const [isGenerating, setIsGenerating] = useState(false);
  const [isSavingTemplate, setIsSavingTemplate] = useState(false);

  const [formError, setFormError] = useState<string | null>(null);
  const [saveTemplateError, setSaveTemplateError] = useState<string | null>(null);

  const lastAppliedTemplateKey = useRef<string | null>(initialTemplate?.id ?? null);

  const sortedCustomTemplates = useMemo(
    () => [...customTemplates].sort((a, b) => a.name.localeCompare(b.name)),
    [customTemplates],
  );

  const loadingTemplates = false;

  const selectedTemplate = useMemo(
    () => resolveTemplateByKey(selectedTemplateKey, builtinTemplatesState, customTemplates),
    [selectedTemplateKey, builtinTemplatesState, customTemplates],
  );

  const resetDialogState = () => {
    const fallbackTemplate = (builtinTemplatesState[0] ?? builtInTemplates[0]) ?? null;
    const fallbackId = fallbackTemplate?.id ?? CUSTOM_TEMPLATE_KEY;
    setSelectedTemplateKey(fallbackId);
    setTemplateBody(fallbackTemplate?.body_md ?? '');
    setHasEditedTemplate(false);
    setFormError(null);
    setSaveTemplateError(null);
    setNewTemplateName('');
    setNewTemplateDescription('');
    setIsGenerating(false);
    setIsSavingTemplate(false);
    lastAppliedTemplateKey.current = fallbackId;
  };

  useEffect(() => {
    if (!open) return;
    setCustomTemplates(loadCustomTemplates());
  }, [open]);

  useEffect(() => {
    if (!open) return;

    if (selectedTemplateKey === CUSTOM_TEMPLATE_KEY) {
      if (lastAppliedTemplateKey.current !== CUSTOM_TEMPLATE_KEY) {
        setTemplateBody('');
        setHasEditedTemplate(false);
        lastAppliedTemplateKey.current = CUSTOM_TEMPLATE_KEY;
      }
      return;
    }

    if (!selectedTemplate) {
      if (lastAppliedTemplateKey.current !== selectedTemplateKey) {
        setTemplateBody('');
        setHasEditedTemplate(false);
        lastAppliedTemplateKey.current = selectedTemplateKey;
      }
      return;
    }

    const shouldApplyTemplate =
      lastAppliedTemplateKey.current !== selectedTemplateKey ||
      (!hasEditedTemplate && lastAppliedTemplateKey.current === selectedTemplateKey);

    if (shouldApplyTemplate) {
      setTemplateBody(selectedTemplate.body_md ?? '');
      setHasEditedTemplate(false);
      lastAppliedTemplateKey.current = selectedTemplateKey;
    }
  }, [selectedTemplateKey, selectedTemplate, open, hasEditedTemplate]);

  useEffect(() => {
    if (selectedTemplateKey === CUSTOM_TEMPLATE_KEY) return;
    if (selectedTemplate) return;
    if (builtinTemplatesState.length === 0) return;

    const fallback = builtinTemplatesState[0];
    setSelectedTemplateKey(fallback.id);
    setTemplateBody(fallback.body_md);
    setHasEditedTemplate(false);
    lastAppliedTemplateKey.current = fallback.id;
  }, [selectedTemplate, selectedTemplateKey, builtinTemplatesState]);

  const handleGenerateReport = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!templateBody.trim()) {
      setFormError('Template body is required.');
      return;
    }

    setIsGenerating(true);
    setFormError(null);

    try {
      const templateName = selectedTemplate?.name ?? 'Custom Report';
      const templateDescription = selectedTemplate?.description ?? '';
      const question = [
        `Generate a comprehensive report for the current notebook using all relevant sources and notes.`,
        `Follow the markdown template titled "${templateName}" exactly. Preserve every heading and replace placeholders with detailed findings. If a section is not applicable, include a short explanation rather than removing the heading.`,
        'Cite notebook sources inline and conclude with a Sources section that references the notebook materials.',
        templateDescription ? `Template summary: ${templateDescription}` : '',
        'Markdown Template:',
        templateBody,
      ]
        .filter(Boolean)
        .join('\n\n');

      const research = await apiClient.runResearch({
        notebook_id: notebookId,
        question,
      });

      const note = await apiClient.createNote({
        notebook_id: notebookId,
        content: research.final_report,
        note_type: 'ai',
        title: selectedTemplate?.name ?? 'Report Draft',
      });

      onReportCreated({ note, research });
      onOpenChange(false);
      resetDialogState();
    } catch (error) {
      console.error('Failed to generate report:', error);
      setFormError('Failed to generate report. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSaveTemplate = async () => {
    const trimmedName = newTemplateName.trim();
    if (!trimmedName || !templateBody.trim()) {
      setSaveTemplateError('Template name and body are required.');
      return;
    }

    const duplicateExists =
      builtinTemplatesState.some((tpl) => tpl.name.toLowerCase() === trimmedName.toLowerCase()) ||
      customTemplates.some((tpl) => tpl.name.toLowerCase() === trimmedName.toLowerCase());

    if (duplicateExists) {
      setSaveTemplateError('A template with this name already exists.');
      return;
    }

    setIsSavingTemplate(true);
    setSaveTemplateError(null);

    try {
      const template: ReportTemplate = {
        id: `custom:${typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : Date.now().toString()}`,
        name: trimmedName,
        description: newTemplateDescription.trim() || null,
        body_md: templateBody,
        scope: 'custom',
        created_at: new Date().toISOString(),
      };

      setCustomTemplates((prev) => {
        const next = [template, ...prev];
        persistCustomTemplates(next);
        return next;
      });
      setSelectedTemplateKey(template.id);
      lastAppliedTemplateKey.current = template.id;
      setShowSaveTemplate(false);
      setNewTemplateName('');
      setNewTemplateDescription('');
    } catch (error) {
      console.error('Failed to save template locally:', error);
      setSaveTemplateError('Failed to save template. Please try again.');
    } finally {
      setIsSavingTemplate(false);
    }
  };

  const builtInOptions = useMemo(() => builtinTemplatesState.map((template) => ({
    key: template.id,
    template,
  })), [builtinTemplatesState]);

  const activeTemplate = selectedTemplateKey === CUSTOM_TEMPLATE_KEY
    ? {
        name: 'Custom (Ad-hoc)',
        description: 'Start from a blank template.',
      }
    : selectedTemplate;

  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {
        onOpenChange(value);
        if (!value) {
          resetDialogState();
        }
      }}
    >
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Create report from sources</DialogTitle>
          <DialogDescription>
            Choose a report template, refine the markdown structure, and generate a fresh report that cites the
            sources in this notebook.
          </DialogDescription>
        </DialogHeader>

        <form className="flex flex-col gap-4" onSubmit={handleGenerateReport}>
          <div className="space-y-2">
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium" htmlFor="report-template-select">
                Report template
              </label>
              <p className="text-xs text-muted-foreground">
                Built-in templates cover common operations. Custom templates let you reuse tailored structures.
              </p>
            </div>
            <Select
              value={selectedTemplateKey}
              onValueChange={(value) => {
                setSelectedTemplateKey(value);
                setHasEditedTemplate(false);
              }}
              disabled={isGenerating || loadingTemplates}
            >
              <SelectTrigger
                id="report-template-select"
                className="items-start justify-start py-2 text-left"
              >
                <div className="flex flex-col">
                  <span className="text-sm font-medium leading-tight">
                    {loadingTemplates
                      ? 'Loading templates…'
                      : activeTemplate?.name ?? 'Select a template…'}
                  </span>
                  {activeTemplate?.description && (
                    <span className="text-xs text-muted-foreground">
                      {activeTemplate.description}
                    </span>
                  )}
                </div>
              </SelectTrigger>
              <SelectContent className="min-w-[360px]">
                <SelectGroup>
                  <SelectLabel>Built-in templates</SelectLabel>
                  {builtInOptions.map(({ key, template }) => (
                    <SelectItem key={key} value={key} className="flex items-start gap-3 py-2">
                      <FileText className="mt-0.5 h-4 w-4 text-primary" />
                      <div className="flex flex-col items-start">
                        <span className="text-sm font-medium leading-tight">{template.name}</span>
                        {template.description && (
                          <span className="text-xs text-muted-foreground">{template.description}</span>
                        )}
                        <Badge variant="outline" className="mt-1 text-xs font-normal">Built-in</Badge>
                      </div>
                    </SelectItem>
                  ))}
                </SelectGroup>
                {sortedCustomTemplates.length > 0 && (
                  <SelectGroup>
                    <SelectLabel>Custom templates</SelectLabel>
                    {sortedCustomTemplates.map((template) => (
                      <SelectItem key={template.id} value={template.id} className="flex items-start gap-3 py-2">
                        <Sparkles className="mt-0.5 h-4 w-4 text-amber-500" />
                        <div className="flex flex-col items-start">
                          <span className="text-sm font-medium leading-tight">{template.name}</span>
                          {template.description && (
                            <span className="text-xs text-muted-foreground">{template.description}</span>
                          )}
                          <Badge variant="outline" className="mt-1 text-xs font-normal text-amber-600 border-amber-200 bg-amber-50">
                            Saved
                          </Badge>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectGroup>
                )}
                <SelectGroup>
                  <SelectLabel>Ad-hoc</SelectLabel>
                  <SelectItem value={CUSTOM_TEMPLATE_KEY} className="flex items-start gap-3 py-2">
                    <PenSquare className="mt-0.5 h-4 w-4 text-muted-foreground" />
                    <div className="flex flex-col items-start">
                      <span className="text-sm font-medium leading-tight">Custom (Ad-hoc)</span>
                      <span className="text-xs text-muted-foreground">Start from a blank slate and save it if you like the result.</span>
                    </div>
                  </SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>
            {selectedTemplate?.description && (
              <p className="text-xs text-muted-foreground">{selectedTemplate.description}</p>
            )}
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="report-template-body">
              Template markdown
            </label>
            <Textarea
              id="report-template-body"
              placeholder="# Title\n\n## Objectives\n- ..."
              value={templateBody}
              onChange={(event) => {
                setTemplateBody(event.target.value);
                setHasEditedTemplate(true);
              }}
              rows={14}
              disabled={isGenerating}
              required
            />
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                Adjust headings, placeholders, and figure/table callouts before generating the report.
              </span>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => {
                  setShowSaveTemplate(true);
                  setSaveTemplateError(null);
                }}
                disabled={!templateBody.trim() || isGenerating}
              >
                Save as template…
              </Button>
            </div>
          </div>

          {formError && (
            <p className="text-sm text-destructive" role="alert">
              {formError}
            </p>
          )}

          <div className="flex items-center justify-end gap-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              disabled={isGenerating}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isGenerating}>
              {isGenerating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating…
                </>
              ) : (
                'Generate report'
              )}
            </Button>
          </div>
        </form>

        <Dialog
          open={showSaveTemplate}
          onOpenChange={(value) => {
            setShowSaveTemplate(value);
            if (!value) {
              setNewTemplateName('');
              setNewTemplateDescription('');
              setSaveTemplateError(null);
              setIsSavingTemplate(false);
            }
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Save as template</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="new-template-name">
                  Template name
                </label>
                <Input
                  id="new-template-name"
                  placeholder="Sea-to-Sky Recovery v1"
                  value={newTemplateName}
                  onChange={(event) => setNewTemplateName(event.target.value)}
                  disabled={isSavingTemplate}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="new-template-description">
                  Description (optional)
                </label>
                <Textarea
                  id="new-template-description"
                  placeholder="Notes about when to use this template…"
                  value={newTemplateDescription}
                  onChange={(event) => setNewTemplateDescription(event.target.value)}
                  rows={3}
                  disabled={isSavingTemplate}
                />
              </div>
              {saveTemplateError && <p className="text-sm text-destructive">{saveTemplateError}</p>}
              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    setShowSaveTemplate(false);
                    setNewTemplateName('');
                    setNewTemplateDescription('');
                    setSaveTemplateError(null);
                  }}
                  disabled={isSavingTemplate}
                >
                  Cancel
                </Button>
                <Button type="button" onClick={handleSaveTemplate} disabled={isSavingTemplate || !templateBody.trim()}>
                  {isSavingTemplate ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving…
                    </>
                  ) : (
                    'Save template'
                  )}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </DialogContent>
    </Dialog>
  );
};

export default GenerateReportDialog;
