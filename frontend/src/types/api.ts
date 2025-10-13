export interface Notebook {
  id: string;
  name: string;
  description: string;
  archived: boolean;
  created: string;
  updated: string;
}

export interface NotebookCreatePayload {
  name: string;
  description?: string;
}

export interface NotebookUpdatePayload {
  name?: string;
  description?: string;
  archived?: boolean;
}

export interface Note {
  id: string;
  title?: string | null;
  content?: string | null;
  note_type?: string | null;
  created: string;
  updated: string;
}

export interface NoteCreatePayload {
  title?: string;
  content: string;
  notebook_id?: string;
  note_type?: string;
}

export interface NoteUpdatePayload {
  title?: string | null;
  content?: string | null;
  note_type?: string | null;
}

export interface SourceAsset {
  file_path?: string | null;
  url?: string | null;
}

export interface SourceListItem {
  id: string;
  title?: string | null;
  topics: string[];
  asset?: SourceAsset | null;
  embedded_chunks: number;
  created: string;
  updated: string;
  insights_count?: number;
}

export interface SourceDetail extends SourceListItem {
  full_text?: string | null;
}

export type SourceCreateType = 'link' | 'upload' | 'text';

export interface SourceCreatePayload {
  notebook_id: string;
  type: SourceCreateType;
  url?: string;
  file_path?: string;
  content?: string;
  title?: string;
  transformations?: string[];
  embed?: boolean;
  delete_source?: boolean;
}

export interface ResearchResponse {
  final_report: string;
  notes: string[];
  research_brief?: string | null;
}

export interface AskResponse {
  question: string;
  answer: string;
}

export interface DefaultModelsResponse {
  default_chat_model?: string | null;
  default_transformation_model?: string | null;
  large_context_model?: string | null;
  default_text_to_speech_model?: string | null;
  default_speech_to_text_model?: string | null;
  default_embedding_model?: string | null;
  default_tools_model?: string | null;
}

export interface ModelItem {
  id: string;
  name: string;
  provider: string;
  type: string;
  created: string;
  updated: string;
}

export interface ModelCreatePayload {
  name: string;
  provider: string;
  type: string;
}

export interface SettingsResponse {
  default_content_processing_engine_doc?: string | null;
  default_content_processing_engine_url?: string | null;
  default_embedding_option?: string | null;
  auto_delete_files?: string | null;
  youtube_preferred_languages?: string[] | null;
}

export interface SettingsUpdatePayload extends Partial<SettingsResponse> {}

export interface ContextConfigRequest {
  notebook_id: string;
  context_config?: {
    sources: Record<string, string>;
    notes: Record<string, string>;
  };
}

export interface ContextResponse {
  notebook_id: string;
  sources: Array<Record<string, unknown>>;
  notes: Array<Record<string, unknown>>;
  total_tokens?: number;
}


export interface Transformation {
  id: string;
  name: string;
  title: string;
  description: string;
  prompt: string;
  apply_default: boolean;
  created: string;
  updated: string;
}

export interface TransformationCreatePayload {
  name: string;
  title: string;
  description: string;
  prompt: string;
  apply_default?: boolean;
}

export interface TransformationUpdatePayload {
  name?: string;
  title?: string;
  description?: string;
  prompt?: string;
  apply_default?: boolean;
}

export interface ModelProvidersResponse {
  available: string[];
  unavailable: string[];
  providers_by_type: Record<string, string[]>;
}

export interface SourceUploadResponse {
  file_path: string;
}
