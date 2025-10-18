import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, Plus, Trash2 } from 'lucide-react';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue, SelectGroup, SelectLabel } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/lib/api-client';
import type {
  DefaultModelsResponse,
  ModelCreatePayload,
  ModelItem,
  ModelProvidersResponse,
  SettingsResponse,
  SettingsUpdatePayload,
} from '@/types/api';

interface SettingsPanelProps {
  onClose?: () => void;
}

const modelTypes: Array<ModelCreatePayload['type']> = [
  'language',
  'embedding',
  'text_to_speech',
  'speech_to_text',
];

const defaultLabelMap: Record<keyof DefaultModelsResponse, string> = {
  default_chat_model: 'Default chat model',
  default_transformation_model: 'Default transformation model',
  large_context_model: 'Large context model',
  default_text_to_speech_model: 'Default text-to-speech model',
  default_speech_to_text_model: 'Default speech-to-text model',
  default_embedding_model: 'Default embedding model',
  default_tools_model: 'Default tools model',
};

const ModelsTab = () => {
  const queryClient = useQueryClient();
  const [newModel, setNewModel] = useState<ModelCreatePayload>({
    name: '',
    provider: '',
    type: 'language',
  });

  const modelsQuery = useQuery<ModelItem[]>({
    queryKey: ['models'],
    queryFn: () => apiClient.getModels(),
  });
  const defaultsQuery = useQuery<DefaultModelsResponse>({
    queryKey: ['model-defaults'],
    queryFn: () => apiClient.getDefaults(),
  });
  const providerInfoQuery = useQuery<ModelProvidersResponse>({
    queryKey: ['model-providers'],
    queryFn: () => apiClient.getModelProviders(),
  });

  const createModelMutation = useMutation<ModelItem, Error, ModelCreatePayload>({
    mutationFn: (payload) => apiClient.createModel(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models'] });
      setNewModel((prev) => ({ ...prev, name: '' }));
    },
  });

  const deleteModelMutation = useMutation<void, Error, string>({
    mutationFn: (modelId) => apiClient.deleteModel(modelId).then(() => undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models'] });
      queryClient.invalidateQueries({ queryKey: ['model-defaults'] });
    },
  });

  const updateDefaultsMutation = useMutation<DefaultModelsResponse, Error, Partial<DefaultModelsResponse>>({
    mutationFn: (payload) => apiClient.updateDefaults(payload),
    onSuccess: (data) => {
      queryClient.setQueryData(['model-defaults'], data);
    },
  });

  const groupedModels = useMemo(() => {
    const groups: Record<string, ModelItem[]> = {};
    (modelsQuery.data ?? []).forEach((model) => {
      if (!groups[model.type]) {
        groups[model.type] = [];
      }
      groups[model.type].push(model);
    });
    return groups;
  }, [modelsQuery.data]);

  const availableProviders = providerInfoQuery.data?.available ?? [];
  const providersByType = providerInfoQuery.data?.providers_by_type ?? {};

  const handleDefaultChange = (key: keyof DefaultModelsResponse, value: string) => {
    updateDefaultsMutation.mutate({ [key]: value === '__none__' ? null : value } as Partial<DefaultModelsResponse>);
  };

  return (
    <div className="flex h-full flex-col gap-6">
      <section className="space-y-4">
        <div>
          <h3 className="text-base font-semibold">Add model</h3>
          <p className="text-xs text-muted-foreground">Register additional models exposed by your providers.</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="space-y-2">
            <label className="text-xs font-medium uppercase text-muted-foreground">Model type</label>
            <Select value={newModel.type} onValueChange={(value) => setNewModel((prev) => ({ ...prev, type: value as ModelCreatePayload['type'] }))}>
              <SelectTrigger>
                <SelectValue placeholder="Select type" />
              </SelectTrigger>
              <SelectContent>
                {modelTypes.map((type) => (
                  <SelectItem key={type} value={type}>
                    {type}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <label className="text-xs font-medium uppercase text-muted-foreground">Provider</label>
            <Select
              value={newModel.provider}
              onValueChange={(value) => setNewModel((prev) => ({ ...prev, provider: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select provider" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectLabel>Available</SelectLabel>
                  {(providersByType[newModel.type] ?? []).map((provider) => (
                    <SelectItem key={provider} value={provider}>
                      <span className="flex items-center justify-between gap-3">
                        <span>{provider}</span>
                        {!availableProviders.includes(provider) && (
                          <Badge variant="outline" className="text-[10px] uppercase">
                            Missing env
                          </Badge>
                        )}
                      </span>
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <label className="text-xs font-medium uppercase text-muted-foreground">Model name</label>
            <Input
              value={newModel.name}
              onChange={(event) => setNewModel((prev) => ({ ...prev, name: event.target.value }))}
              placeholder="gpt-4o-mini"
            />
          </div>
        </div>
        <Button
          onClick={() => createModelMutation.mutate(newModel)}
          disabled={!newModel.name.trim() || !newModel.provider || createModelMutation.isPending}
        >
          {createModelMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Plus className="mr-2 h-4 w-4" />}Add model
        </Button>
      </section>

      <section className="space-y-3">
        <div>
          <h3 className="text-base font-semibold">Default assignments</h3>
          <p className="text-xs text-muted-foreground">Select which models power chat, transformations, and embeddings.</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {([
            'default_chat_model',
            'default_transformation_model',
            'default_embedding_model',
          ] as Array<keyof DefaultModelsResponse>).map((key) => (
            <div key={key} className="space-y-2 rounded-md border border-border/70 bg-card/60 p-4">
              <div>
                <div className="text-sm font-medium">
                  {defaultLabelMap[key] ?? key.replace(/_/g, ' ')}
                </div>
              </div>
              <Select
                value={defaultsQuery.data?.[key] ?? '__none__'}
                onValueChange={(value) => handleDefaultChange(key, value)}
                disabled={updateDefaultsMutation.isPending || (groupedModels[key === 'default_embedding_model' ? 'embedding' : 'language'] ?? []).length === 0}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select model" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">None</SelectItem>
                  {(groupedModels[key === 'default_embedding_model' ? 'embedding' : 'language'] ?? []).map((model) => (
                    <SelectItem key={model.id} value={model.id}>
                      {model.provider}/{model.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold">Configured models</h3>
          <div className="text-xs text-muted-foreground">
            {availableProviders.length > 0 && (
              <span>Available providers: {availableProviders.join(', ')}</span>
            )}
          </div>
        </div>
        <div className="space-y-2">
          {modelsQuery.isLoading && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading models…
            </div>
          )}
          {!modelsQuery.isLoading && (modelsQuery.data?.length ?? 0) === 0 && (
            <div className="rounded-md border border-dashed p-4 text-xs text-muted-foreground">
              No models registered yet.
            </div>
          )}
          {(modelsQuery.data ?? []).map((model) => (
            <div
              key={model.id}
              className="flex items-center justify-between rounded-md border border-border/60 bg-background px-3 py-2"
            >
              <div>
                <div className="text-sm font-medium text-foreground">{model.provider}/{model.name}</div>
                <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{model.type}</div>
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => deleteModelMutation.mutate(model.id)}
                disabled={deleteModelMutation.isPending}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};


const SettingsTab = () => {
  const queryClient = useQueryClient();
  const settingsQuery = useQuery<SettingsResponse>({
    queryKey: ['settings'],
    queryFn: () => apiClient.getSettings(),
  });
  const updateSettingsMutation = useMutation<SettingsResponse, Error, SettingsUpdatePayload>({
    mutationFn: (payload) => apiClient.updateSettings(payload),
    onSuccess: (data) => {
      queryClient.setQueryData(['settings'], data);
    },
  });

  const [formState, setFormState] = useState<SettingsUpdatePayload>({});

  const handleFieldChange = (key: keyof SettingsUpdatePayload, value: string | null) => {
    setFormState((prev) => ({ ...prev, [key]: value }));
  };

  const handleEmbeddingOptionChange = (value: string) => {
    handleFieldChange('default_embedding_option', value === 'never' ? 'never' : value);
  };

  const handleLanguagesChange = (value: string) => {
    const languages = value
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
    setFormState((prev) => ({ ...prev, youtube_preferred_languages: languages.length ? languages : null }));
  };

  const handleSubmit = () => {
    updateSettingsMutation.mutate(formState);
  };

  const effectiveForm = { ...settingsQuery.data, ...formState };

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <label className="text-xs font-medium uppercase text-muted-foreground">
            Default content processing doc engine
          </label>
          <Input
            value={effectiveForm.default_content_processing_engine_doc ?? ''}
            onChange={(event) => handleFieldChange('default_content_processing_engine_doc', event.target.value || null)}
            placeholder="doc processing engine"
          />
        </div>
        <div className="space-y-2">
          <label className="text-xs font-medium uppercase text-muted-foreground">
            Default content processing URL engine
          </label>
          <Input
            value={effectiveForm.default_content_processing_engine_url ?? ''}
            onChange={(event) => handleFieldChange('default_content_processing_engine_url', event.target.value || null)}
            placeholder="url processing engine"
          />
        </div>
        <div className="space-y-2">
          <label className="text-xs font-medium uppercase text-muted-foreground">
            Default embedding option
          </label>
          <Select
            value={effectiveForm.default_embedding_option ?? 'never'}
            onValueChange={handleEmbeddingOptionChange}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select option" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="always">Always embed</SelectItem>
              <SelectItem value="ask">Ask each time</SelectItem>
              <SelectItem value="never">Never embed</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <label className="text-xs font-medium uppercase text-muted-foreground">Auto delete files</label>
          <Select
            value={effectiveForm.auto_delete_files ?? 'no'}
            onValueChange={(value) => handleFieldChange('auto_delete_files', value)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select option" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="yes">Yes</SelectItem>
              <SelectItem value="no">No</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="space-y-2">
        <label className="text-xs font-medium uppercase text-muted-foreground">
          YouTube preferred languages (comma separated)
        </label>
        <Input
          value={(effectiveForm.youtube_preferred_languages ?? []).join(', ')}
          onChange={(event) => handleLanguagesChange(event.target.value)}
          placeholder="en, pt"
        />
      </div>
      <Button
        className="mt-2 w-fit"
        onClick={handleSubmit}
        disabled={updateSettingsMutation.isPending}
      >
        {updateSettingsMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
        Save settings
      </Button>
    </div>
  );
};

const SettingsPanel = ({ onClose }: SettingsPanelProps) => {
  const [activeTab, setActiveTab] = useState<'models' | 'settings'>('models');

  return (
    <div className="flex h-full flex-col gap-4">
      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as typeof activeTab)} className="flex h-full flex-col">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="models">Models</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>
        <div className="flex-1 overflow-y-auto py-4">
          <TabsContent value="models" className="h-full">
            <ModelsTab />
          </TabsContent>
          <TabsContent value="settings" className="h-full">
            <SettingsTab />
          </TabsContent>
        </div>
      </Tabs>
      {onClose && (
        <div className="flex justify-end border-t pt-4">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>
      )}
    </div>
  );
};

export default SettingsPanel;
