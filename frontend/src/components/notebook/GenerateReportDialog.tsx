import { useEffect, useMemo, useState } from "react";
import { FileText, Loader2, PenSquare, Sparkles } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SelectItemText } from "@radix-ui/react-select";
import builtinTemplatesRaw from "@/components/notebook/templates/builtin-templates";
import { apiClient } from "@/lib/api-client";
import type { ResearchResponse } from "@/types/api";

type TemplateScope = "builtin" | "custom";

type ReportTemplate = {
  id: string;
  name: string;
  description: string | null;
  body_md: string;
  scope: TemplateScope;
  created_at?: string;
};

const CUSTOM_TEMPLATE_KEY = "custom:adhoc";
const CUSTOM_TEMPLATE_STORAGE_KEY = "open-notebook:report-templates";

const builtInTemplates: ReportTemplate[] = builtinTemplatesRaw.map(
  (template) => ({
    ...template,
    scope: "builtin" as const,
    created_at: undefined,
  })
);

const loadCustomTemplates = (): ReportTemplate[] => {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(CUSTOM_TEMPLATE_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((item) => ({
        id:
          typeof item.id === "string"
            ? item.id
            : `custom:${crypto.randomUUID?.() ?? Date.now()}`,
        name: typeof item.name === "string" ? item.name : "Custom Template",
        description:
          typeof item.description === "string" ? item.description : null,
        body_md: typeof item.body_md === "string" ? item.body_md : "",
        scope: "custom" as const,
        created_at:
          typeof item.created_at === "string"
            ? item.created_at
            : new Date().toISOString(),
      }))
      .filter((item) => item.body_md.trim().length > 0);
  } catch (error) {
    console.error("Failed to load custom templates from storage:", error);
    return [];
  }
};

const persistCustomTemplates = (templates: ReportTemplate[]) => {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      CUSTOM_TEMPLATE_STORAGE_KEY,
      JSON.stringify(
        templates.map((template) => ({
          ...template,
          scope: "custom",
        }))
      )
    );
  } catch (error) {
    console.error("Failed to persist custom templates:", error);
  }
};

const resolveTemplateByKey = (
  key: string,
  builtins: ReportTemplate[],
  custom: ReportTemplate[]
): ReportTemplate | null => {
  if (key === CUSTOM_TEMPLATE_KEY) return null;
  const all = [...builtins, ...custom];
  return all.find((template) => template.id === key) ?? null;
};

interface GenerateReportDialogProps {
  open: boolean;
  notebookId: string;
  onOpenChange: (open: boolean) => void;
  onReportCreated: (payload: { research: ResearchResponse }) => void;
}

const GenerateReportDialog = ({
  open,
  notebookId,
  onOpenChange,
  onReportCreated,
}: GenerateReportDialogProps) => {
  const builtinTemplatesState = builtInTemplates;
  const [customTemplates, setCustomTemplates] = useState<ReportTemplate[]>([]);

  const [selectedTemplateKey, setSelectedTemplateKey] = useState<string>("");
  const [templateBody, setTemplateBody] = useState<string>("");

  const [showSaveTemplate, setShowSaveTemplate] = useState(false);
  const [newTemplateName, setNewTemplateName] = useState("");
  const [newTemplateDescription, setNewTemplateDescription] = useState("");

  const [isGenerating, setIsGenerating] = useState(false);
  const [isSavingTemplate, setIsSavingTemplate] = useState(false);
  const [saveTemplateMode, setSaveTemplateMode] = useState<"create" | "update">(
    "create"
  );
  const [templateToUpdate, setTemplateToUpdate] =
    useState<ReportTemplate | null>(null);

  const [formError, setFormError] = useState<string | null>(null);
  const [saveTemplateError, setSaveTemplateError] = useState<string | null>(
    null
  );

  const sortedCustomTemplates = useMemo(
    () => [...customTemplates].sort((a, b) => a.name.localeCompare(b.name)),
    [customTemplates]
  );

  const loadingTemplates = false;
  const selectPlaceholder = loadingTemplates
    ? "Loading templates…"
    : "Select a template…";

  const selectedTemplate = useMemo(
    () =>
      resolveTemplateByKey(
        selectedTemplateKey,
        builtinTemplatesState,
        customTemplates
      ),
    [selectedTemplateKey, builtinTemplatesState, customTemplates]
  );

  // prevent scroll chaining jitter at edges of the dropdown
  const onWheelCapture: React.WheelEventHandler<HTMLDivElement> = (e) => {
    const el = e.currentTarget;
    const delta = e.deltaY;
    const atTop = el.scrollTop <= 0 && delta < 0;
    const atBottom =
      Math.ceil(el.scrollTop + el.clientHeight) >= el.scrollHeight && delta > 0;
    if (atTop || atBottom) {
      e.preventDefault();
      e.stopPropagation();
    }
  };

  const handleTemplateSelection = (value: string) => {
    const resolved = resolveTemplateByKey(
      value,
      builtinTemplatesState,
      customTemplates
    );
    setSelectedTemplateKey(value);
    setTemplateToUpdate(null);
    setSaveTemplateMode("create");
    setNewTemplateName("");
    setNewTemplateDescription("");
    setSaveTemplateError(null);
    if (value === CUSTOM_TEMPLATE_KEY) {
      if (selectedTemplateKey !== CUSTOM_TEMPLATE_KEY) {
        setTemplateBody("");
      }
    } else if (resolved) {
      setTemplateBody(resolved.body_md ?? "");
    } else {
      setTemplateBody("");
    }
  };

  const startSaveTemplateFlow = () => {
    setSaveTemplateError(null);
    if (selectedTemplate && selectedTemplate.scope === "custom") {
      setSaveTemplateMode("update");
      setTemplateToUpdate(selectedTemplate);
      setNewTemplateName(selectedTemplate.name);
      setNewTemplateDescription(selectedTemplate.description ?? "");
    } else if (selectedTemplate) {
      setSaveTemplateMode("create");
      setTemplateToUpdate(null);
      setNewTemplateName(`${selectedTemplate.name} copy`.trim());
      setNewTemplateDescription(selectedTemplate.description ?? "");
    } else {
      setSaveTemplateMode("create");
      setTemplateToUpdate(null);
      setNewTemplateName("");
      setNewTemplateDescription("");
    }
    setShowSaveTemplate(true);
  };

  const resetDialogState = () => {
    setSelectedTemplateKey("");
    setTemplateBody("");
    setFormError(null);
    setSaveTemplateError(null);
    setNewTemplateName("");
    setNewTemplateDescription("");
    setIsGenerating(false);
    setIsSavingTemplate(false);
    setSaveTemplateMode("create");
    setTemplateToUpdate(null);
  };

  useEffect(() => {
    if (!open) return;
    setCustomTemplates(loadCustomTemplates());
  }, [open]);

  useEffect(() => {
    if (!open) return;
    if (!selectedTemplateKey || selectedTemplateKey === CUSTOM_TEMPLATE_KEY)
      return;

    const resolved = resolveTemplateByKey(
      selectedTemplateKey,
      builtinTemplatesState,
      customTemplates
    );
    if (!resolved) {
      setSelectedTemplateKey("");
      setTemplateBody("");
    }
  }, [selectedTemplateKey, builtinTemplatesState, customTemplates, open]);

  const handleGenerateReport = async (
    event: React.FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    if (!templateBody.trim()) {
      setFormError("Template body is required.");
      return;
    }

    setIsGenerating(true);
    setFormError(null);

    try {
      const templateName = selectedTemplate?.name ?? "Custom Report";
      const templateDescription = selectedTemplate?.description ?? "";
      const question = [
        `Generate a comprehensive report for the current notebook using all relevant sources and notes.`,
        `Follow the markdown template titled "${templateName}" exactly. Preserve every heading and replace placeholders with detailed findings.`,
        `If a section is not applicable, include a short explanation rather than removing the heading.`,
        "Cite notebook sources inline and conclude with a Sources section that references the notebook materials.",
        templateDescription ? `Template summary: ${templateDescription}` : "",
        "Markdown Template:",
        templateBody,
      ]
        .filter(Boolean)
        .join("\n\n");

      const research = await apiClient.runResearch({
        notebook_id: notebookId,
        question,
      });

      // retired notes from notebook

      // const note = await apiClient.createNote({
      //   notebook_id: notebookId,
      //   content: research.final_report,
      //   note_type: "ai",
      //   title: selectedTemplate?.name ?? "Report Draft",
      // });

      // onReportCreated({ note, research });
      onReportCreated({ research });
      onOpenChange(false);
      resetDialogState();
    } catch (error) {
      console.error("Failed to generate report:", error);
      setFormError("Failed to generate report. Please try again.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSaveTemplate = async (action: "create" | "update") => {
    const trimmedBody = templateBody.trim();
    const trimmedName = newTemplateName.trim();
    const trimmedDescription = newTemplateDescription.trim();

    if (!trimmedBody) {
      setSaveTemplateError("Template body is required.");
      return;
    }
    if (!trimmedName) {
      setSaveTemplateError("Template name is required.");
      return;
    }

    const nameConflicts = (excludeId?: string) =>
      builtinTemplatesState.some(
        (tpl) => tpl.name.toLowerCase() === trimmedName.toLowerCase()
      ) ||
      customTemplates.some(
        (tpl) =>
          tpl.id !== excludeId &&
          tpl.name.toLowerCase() === trimmedName.toLowerCase()
      );

    if (action === "update" && !templateToUpdate) {
      console.warn(
        "Requested template update without a target; falling back to create."
      );
      return handleSaveTemplate("create");
    }
    if (action === "create" && nameConflicts()) {
      setSaveTemplateError("A template with this name already exists.");
      return;
    }
    if (
      action === "update" &&
      templateToUpdate &&
      nameConflicts(templateToUpdate.id)
    ) {
      setSaveTemplateError("Another template already uses this name.");
      return;
    }

    setIsSavingTemplate(true);
    setSaveTemplateError(null);

    try {
      if (action === "update" && templateToUpdate) {
        const updatedTemplate: ReportTemplate = {
          ...templateToUpdate,
          name: trimmedName,
          description: trimmedDescription ? trimmedDescription : null,
          body_md: templateBody,
          created_at: templateToUpdate.created_at ?? new Date().toISOString(),
        };

        setCustomTemplates((prev) => {
          const next = prev.map((tpl) =>
            tpl.id === updatedTemplate.id ? updatedTemplate : tpl
          );
          persistCustomTemplates(next);
          return next;
        });
        setSelectedTemplateKey(updatedTemplate.id);
        setTemplateBody(updatedTemplate.body_md);
      } else {
        const newTemplate: ReportTemplate = {
          id: `custom:${
            typeof crypto !== "undefined" && crypto.randomUUID
              ? crypto.randomUUID()
              : Date.now().toString()
          }`,
          name: trimmedName,
          description: trimmedDescription ? trimmedDescription : null,
          body_md: templateBody,
          scope: "custom",
          created_at: new Date().toISOString(),
        };

        setCustomTemplates((prev) => {
          const next = [newTemplate, ...prev];
          persistCustomTemplates(next);
          return next;
        });
        setSelectedTemplateKey(newTemplate.id);
        setTemplateBody(newTemplate.body_md);
      }

      setShowSaveTemplate(false);
      setNewTemplateName("");
      setNewTemplateDescription("");
      setTemplateToUpdate(null);
      setSaveTemplateMode("create");
    } catch (error) {
      console.error("Failed to store custom template:", error);
      setSaveTemplateError("Failed to save template. Please try again.");
    } finally {
      setIsSavingTemplate(false);
    }
  };

  const builtInOptions = useMemo(
    () =>
      builtinTemplatesState.map((template) => ({ key: template.id, template })),
    [builtinTemplatesState]
  );

  const activeTemplateDescription =
    selectedTemplateKey === CUSTOM_TEMPLATE_KEY
      ? "Start from a blank template."
      : selectedTemplate?.description ?? null;

  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {
        onOpenChange(value);
        if (!value) resetDialogState();
      }}
    >
      {/* Fit within viewport and scroll inside */}
      <DialogContent className="sm:max-w-2xl p-0 rounded-2xl border shadow-2xl">
        <div className="flex max-h-[85vh] flex-col">
          {/* Sticky header */}
          <DialogHeader className="select-none cursor-default sticky top-0 z-10 bg-background/95 backdrop-blur px-6 py-4 border-b">
            <DialogTitle className="text-lg">
              Create report from sources
            </DialogTitle>
            <DialogDescription>
              Choose a report template, refine the markdown structure, and
              generate a fresh report that cites the sources in this notebook.
            </DialogDescription>
          </DialogHeader>

          {/* Scrollable body */}
          <div className="flex-1 overflow-y-auto px-6 py-4">
            <form
              className="flex flex-col gap-4"
              onSubmit={handleGenerateReport}
            >
              <div className="space-y-2 select-none cursor-default">
                <div className="flex flex-col gap-1">
                  <label
                    className="text-sm font-medium"
                    htmlFor="report-template-select"
                  >
                    Report template
                  </label>
                  <p className="text-xs text-muted-foreground">
                    Built-in templates cover common operations. Custom templates
                    let you reuse tailored structures.
                  </p>
                </div>

                <Select
                  value={selectedTemplateKey || undefined}
                  onValueChange={handleTemplateSelection}
                  disabled={isGenerating || loadingTemplates}
                >
                  <SelectTrigger
                    id="report-template-select"
                    className="items-start justify-start py-2 text-left cursor-pointer"
                  >
                    <SelectValue placeholder={selectPlaceholder} />
                  </SelectTrigger>

                  {/* Animated, scrollable dropdown; popper avoids clipping */}
                  <SelectContent
                    position="popper"
                    side="bottom"
                    sideOffset={8}
                    avoidCollisions
                    className="
                      min-w-[380px]
                      rounded-xl border shadow-lg
                      data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95
                      data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95
                    "
                  >
                    <div
                      onWheelCapture={onWheelCapture}
                      className="max-h-80 overflow-y-auto overscroll-contain"
                    >
                      <SelectGroup className="select-none cursor-default">
                        <SelectLabel
                          className="sticky top-0 z-10 px-3 py-2 text-[11px] uppercase tracking-wide text-muted-foreground/80
                                     bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-b"
                        >
                          Built-in templates
                        </SelectLabel>
                        <div className="py-1">
                          {builtInOptions.map(({ key, template }) => (
                            <SelectItem
                              key={key}
                              value={key}
                              className="py-2 px-2"
                            >
                              <div className="flex w-full items-start gap-3">
                                <FileText className="mt-0.5 h-4 w-4 text-primary" />
                                <div className="flex flex-col items-start text-left">
                                  <SelectItemText className="text-sm font-medium leading-tight">
                                    {template.name}
                                  </SelectItemText>
                                  {template.description && (
                                    <span className="text-xs text-muted-foreground">
                                      {template.description}
                                    </span>
                                  )}
                                  <Badge
                                    variant="outline"
                                    className="mt-1 text-[10px] font-normal"
                                  >
                                    Built-in
                                  </Badge>
                                </div>
                              </div>
                            </SelectItem>
                          ))}
                        </div>
                      </SelectGroup>

                      {sortedCustomTemplates.length > 0 && (
                        <SelectGroup className="select-none cursor-default">
                          <SelectLabel
                            className="sticky top-0 z-10 px-3 py-2 text-[11px] uppercase tracking-wide text-muted-foreground/80
                                       bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-y"
                          >
                            Custom templates
                          </SelectLabel>
                          <div className="py-1">
                            {sortedCustomTemplates.map((template) => (
                              <SelectItem
                                key={template.id}
                                value={template.id}
                                className="py-2 px-2"
                              >
                                <div className="flex w-full items-start gap-3">
                                  <Sparkles className="mt-0.5 h-4 w-4 text-amber-500" />
                                  <div className="flex flex-col items-start text-left">
                                    <SelectItemText className="text-sm font-medium leading-tight">
                                      {template.name}
                                    </SelectItemText>
                                    {template.description && (
                                      <span className="text-xs text-muted-foreground">
                                        {template.description}
                                      </span>
                                    )}
                                    <Badge
                                      variant="outline"
                                      className="mt-1 text-[10px] font-normal text-amber-600 border-amber-200 bg-amber-50"
                                    >
                                      Saved
                                    </Badge>
                                  </div>
                                </div>
                              </SelectItem>
                            ))}
                          </div>
                        </SelectGroup>
                      )}

                      <SelectGroup className="select-none cursor-default">
                        <SelectLabel
                          className="sticky top-0 z-10 px-3 py-2 text-[11px] uppercase tracking-wide text-muted-foreground/80
                                     bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-y"
                        >
                          Ad-hoc
                        </SelectLabel>
                        <div className="py-1">
                          <SelectItem
                            value={CUSTOM_TEMPLATE_KEY}
                            className="py-2 px-2"
                          >
                            <div className="flex w-full items-start gap-3">
                              <PenSquare className="mt-0.5 h-4 w-4 text-muted-foreground" />
                              <div className="flex flex-col items-start text-left">
                                <SelectItemText className="text-sm font-medium leading-tight">
                                  Custom (Ad-hoc)
                                </SelectItemText>
                                <span className="text-xs text-muted-foreground">
                                  Start from a blank slate and save it if you
                                  like the result.
                                </span>
                              </div>
                            </div>
                          </SelectItem>
                        </div>
                      </SelectGroup>
                    </div>
                  </SelectContent>
                </Select>

                {activeTemplateDescription && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    {activeTemplateDescription}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <label
                  className="text-sm font-medium select-none cursor-default"
                  htmlFor="report-template-body"
                >
                  Template
                </label>
                <Textarea
                  id="report-template-body"
                  placeholder="Insert your report format here, using headings, placeholders, and figure/table callouts as needed."
                  value={templateBody}
                  onChange={(event) => setTemplateBody(event.target.value)}
                  rows={14}
                  disabled={isGenerating}
                  required
                  className="font-mono leading-6 resize-y min-h-64"
                />
                <div className="flex items-center justify-between select-none cursor-default">
                  <span className="text-xs text-muted-foreground">
                    Adjust headings, placeholders, and figure/table callouts
                    before generating the report.
                  </span>
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={startSaveTemplateFlow}
                    disabled={!templateBody.trim() || isGenerating}
                    className="cursor-pointer"
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

              {/* Sticky action bar so actions are always reachable */}
              <div className="sticky bottom-0 z-10 -mx-6 mt-2 bg-background/95 backdrop-blur px-6 py-3 border-t flex items-center justify-end gap-2 select-none cursor-default">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => onOpenChange(false)}
                  disabled={isGenerating}
                  className="cursor-pointer"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={isGenerating}
                  className="cursor-pointer"
                >
                  {isGenerating ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Generating…
                    </>
                  ) : (
                    "Generate report"
                  )}
                </Button>
              </div>
            </form>
          </div>
        </div>

        {/* Nested: Save/Update Template dialog, also constrained + scrollable */}
        <Dialog
          open={showSaveTemplate}
          onOpenChange={(value) => {
            setShowSaveTemplate(value);
            if (!value) {
              setNewTemplateName("");
              setNewTemplateDescription("");
              setSaveTemplateError(null);
              setIsSavingTemplate(false);
              setTemplateToUpdate(null);
              setSaveTemplateMode("create");
            }
          }}
        >
          <DialogContent className="p-0 rounded-xl">
            <div className="flex max-h-[75vh] flex-col">
              <DialogHeader className="select-none cursor-default sticky top-0 z-10 bg-background/95 backdrop-blur px-6 py-4 border-b">
                <DialogTitle>
                  {saveTemplateMode === "update"
                    ? "Update template"
                    : "Save as template"}
                </DialogTitle>
                {saveTemplateMode === "update" && templateToUpdate && (
                  <DialogDescription>
                    Update &quot;{templateToUpdate.name}&quot; in place or save
                    a brand new template instead.
                  </DialogDescription>
                )}
              </DialogHeader>

              <div className="flex-1 overflow-y-auto px-6 py-4">
                <div className="space-y-3">
                  <div className="space-y-2">
                    <label
                      className="text-sm font-medium select-none cursor-default"
                      htmlFor="new-template-name"
                    >
                      Template name
                    </label>
                    <Input
                      id="new-template-name"
                      placeholder="Sea-to-Sky Recovery v1"
                      value={newTemplateName}
                      onChange={(event) =>
                        setNewTemplateName(event.target.value)
                      }
                      disabled={isSavingTemplate}
                    />
                  </div>
                  <div className="space-y-2">
                    <label
                      className="text-sm font-medium select-none cursor-default"
                      htmlFor="new-template-description"
                    >
                      Description (optional)
                    </label>
                    <Textarea
                      id="new-template-description"
                      placeholder="Notes about when to use this template…"
                      value={newTemplateDescription}
                      onChange={(event) =>
                        setNewTemplateDescription(event.target.value)
                      }
                      rows={3}
                      disabled={isSavingTemplate}
                    />
                  </div>
                  {saveTemplateError && (
                    <p className="text-sm text-destructive">
                      {saveTemplateError}
                    </p>
                  )}
                </div>
              </div>

              <div className="sticky bottom-0 z-10 bg-background/95 backdrop-blur px-6 py-3 border-t flex flex-wrap justify-end gap-2 select-none cursor-default">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    setShowSaveTemplate(false);
                    setNewTemplateName("");
                    setNewTemplateDescription("");
                    setSaveTemplateError(null);
                    setTemplateToUpdate(null);
                    setSaveTemplateMode("create");
                  }}
                  disabled={isSavingTemplate}
                  className="cursor-pointer"
                >
                  Cancel
                </Button>
                {saveTemplateMode === "update" && (
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => handleSaveTemplate("create")}
                    disabled={isSavingTemplate || !templateBody.trim()}
                    className="cursor-pointer"
                  >
                    Save as new template
                  </Button>
                )}
                <Button
                  type="button"
                  onClick={() => handleSaveTemplate(saveTemplateMode)}
                  disabled={isSavingTemplate || !templateBody.trim()}
                  className="cursor-pointer"
                >
                  {isSavingTemplate ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving…
                    </>
                  ) : saveTemplateMode === "update" ? (
                    "Update template"
                  ) : (
                    "Save template"
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
