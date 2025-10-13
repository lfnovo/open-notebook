import axios, { AxiosError } from 'axios';

import { getApiBaseUrl } from './env';
import type {
  AskResponse,
  ContextConfigRequest,
  ContextResponse,
  DefaultModelsResponse,
  EmbedResponse,
  ModelCreatePayload,
  ModelItem,
  ModelProvidersResponse,
  Notebook,
  NotebookCreatePayload,
  NotebookUpdatePayload,
  Note,
  NoteCreatePayload,
  NoteUpdatePayload,
  ResearchResponse,
  SettingsResponse,
  SettingsUpdatePayload,
  SourceCreatePayload,
  SourceDetail,
  SourceListItem,
  SourceUploadResponse,
  Transformation,
  TransformationCreatePayload,
  TransformationUpdatePayload,
} from '@/types/api';

const api = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 120000,
});

const unwrap = <T>(promise: Promise<{ data: T }>): Promise<T> =>
  promise.then((response) => response.data);

export const apiClient = {
  getNotebooks: () => unwrap<Notebook[]>(api.get('/notebooks')),
  getNotebook: (notebookId: string) => unwrap<Notebook>(api.get(`/notebooks/${notebookId}`)),
  createNotebook: (payload: NotebookCreatePayload) =>
    unwrap<Notebook>(api.post('/notebooks', payload)),
  updateNotebook: (notebookId: string, payload: NotebookUpdatePayload) =>
    unwrap<Notebook>(api.put(`/notebooks/${notebookId}`, payload)),
  deleteNotebook: (notebookId: string) => api.delete(`/notebooks/${notebookId}`),

  getNotes: (notebookId?: string) =>
    unwrap<Note[]>(api.get('/notes', { params: notebookId ? { notebook_id: notebookId } : undefined })),
  createNote: (payload: NoteCreatePayload) => unwrap<Note>(api.post('/notes', payload)),
  updateNote: (noteId: string, payload: NoteUpdatePayload) =>
    unwrap<Note>(api.put(`/notes/${noteId}`, payload)),
  deleteNote: (noteId: string) => api.delete(`/notes/${noteId}`),

  getSources: (notebookId?: string) =>
    unwrap<SourceListItem[]>(api.get('/sources', { params: notebookId ? { notebook_id: notebookId } : undefined })),
  getSource: (sourceId: string) => unwrap<SourceDetail>(api.get(`/sources/${sourceId}`)),
  uploadSourceFile: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return unwrap<SourceUploadResponse>(
      api.post('/sources/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
    );
  },
  createSource: (payload: SourceCreatePayload) => unwrap<SourceDetail>(api.post('/sources', payload)),
  deleteSource: (sourceId: string) => api.delete(`/sources/${sourceId}`),
  embedContent: (payload: { item_id: string; item_type: string }) =>
    unwrap<EmbedResponse>(api.post('/embed', payload)),

  runResearch: (payload: { question: string; notebook_id?: string; config_overrides?: Record<string, unknown> }) =>
    unwrap<ResearchResponse>(api.post('/search/research', payload)),

  ask: (payload: { question: string; strategy_model: string; answer_model: string; final_answer_model: string }) =>
    unwrap<AskResponse>(api.post('/search/ask/simple', payload)),

  getTransformations: () => unwrap<Transformation[]>(api.get('/transformations')),
  createTransformation: (payload: TransformationCreatePayload) =>
    unwrap<Transformation>(api.post('/transformations', payload)),
  updateTransformation: (transformationId: string, payload: TransformationUpdatePayload) =>
    unwrap<Transformation>(api.put(`/transformations/${transformationId}`, payload)),
  deleteTransformation: (transformationId: string) => api.delete(`/transformations/${transformationId}`),

  getDefaults: () => unwrap<DefaultModelsResponse>(api.get('/models/defaults')),
  updateDefaults: (payload: Partial<DefaultModelsResponse>) => unwrap<DefaultModelsResponse>(api.put('/models/defaults', payload)),
  getModelProviders: () => unwrap<ModelProvidersResponse>(api.get('/models/providers')),
  getModels: (type?: string) => unwrap<ModelItem[]>(api.get('/models', { params: type ? { type } : undefined })),
  createModel: (payload: ModelCreatePayload) => unwrap<ModelItem>(api.post('/models', payload)),
  deleteModel: (modelId: string) => api.delete(`/models/${modelId}`),

  getSettings: () => unwrap<SettingsResponse>(api.get('/settings')),
  updateSettings: (payload: SettingsUpdatePayload) => unwrap<SettingsResponse>(api.put('/settings', payload)),

  getContext: (payload: ContextConfigRequest) =>
    unwrap<ContextResponse>(api.post(`/notebooks/${payload.notebook_id}/context`, payload)),
};

export const isAxiosError = (error: unknown): error is AxiosError => axios.isAxiosError(error);
