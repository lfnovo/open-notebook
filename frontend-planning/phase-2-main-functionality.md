# Phase 2: Main Functionality Implementation Guide

## Overview

Phase 2 implements the core functionality of Open Notebook, including the notebooks page with three-column layout, source and note management, basic chat interface, and settings page. This phase builds upon the Phase 1 infrastructure to deliver the primary user workflows.

## Prerequisites from Phase 1

✅ **Completed in Phase 1:**
- Next.js 14 project with TypeScript and Tailwind CSS
- Shadcn/UI components library setup
- Authentication system with Zustand store
- API client with Bearer token authentication
- Navigation and layout components (AppSidebar, AppHeader, AppShell)
- Basic page routing and middleware
- All placeholder pages created

## Technology Additions for Phase 2

- **React Query**: For server state management and caching (moved from Phase 1)
- **React Hook Form**: For form handling and validation
- **React DnD**: For drag-and-drop file uploads
- **Monaco Editor**: For markdown editing
- **Date-fns**: For date formatting and manipulation
- **React Markdown**: For markdown rendering

## Project Structure Additions

```
src/
├── app/
│   ├── (dashboard)/
│   │   ├── notebooks/
│   │   │   ├── page.tsx
│   │   │   ├── [id]/
│   │   │   │   └── page.tsx
│   │   │   └── components/
│   │   │       ├── NotebookList.tsx
│   │   │       ├── NotebookCard.tsx
│   │   │       ├── CreateNotebookForm.tsx
│   │   │       ├── NotebookHeader.tsx
│   │   │       ├── SourcesColumn.tsx
│   │   │       ├── NotesColumn.tsx
│   │   │       ├── ChatColumn.tsx
│   │   │       ├── SourceCard.tsx
│   │   │       ├── NoteCard.tsx
│   │   │       ├── AddSourceDialog.tsx
│   │   │       ├── AddNoteDialog.tsx
│   │   │       ├── SourcePanel.tsx
│   │   │       └── NotePanel.tsx
│   │   └── settings/
│   │       ├── page.tsx
│   │       └── components/
│   │           ├── SettingsForm.tsx
│   │           ├── ProcessingSettings.tsx
│   │           ├── FileSettings.tsx
│   │           └── LanguageSettings.tsx
├── components/
│   ├── ui/
│   │   ├── file-upload.tsx
│   │   ├── monaco-editor.tsx
│   │   └── context-indicator.tsx
│   └── common/
│       ├── ConfirmDialog.tsx
│       ├── DateDisplay.tsx
│       └── EmptyState.tsx
├── lib/
│   ├── api/
│   │   ├── notes.ts
│   │   └── sources.ts
│   ├── hooks/
│   │   ├── use-notebooks.ts
│   │   ├── use-notes.ts
│   │   ├── use-sources.ts
│   │   ├── use-settings.ts
│   │   └── use-file-upload.ts
│   ├── stores/
│   │   ├── notebook-store.ts
│   │   └── ui-store.ts
│   └── utils/
│       ├── date.ts
│       ├── file.ts
│       └── validation.ts
```

---

## 1. Data Management Layer

### 1.1 React Query Setup (`lib/api/query-client.ts`)

```typescript
import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes
      retry: 2,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 1,
    },
  },
})

export const QUERY_KEYS = {
  notebooks: ['notebooks'] as const,
  notebook: (id: string) => ['notebooks', id] as const,
  notes: (notebookId?: string) => ['notes', notebookId] as const,
  note: (id: string) => ['notes', id] as const,
  sources: (notebookId?: string) => ['sources', notebookId] as const,
  source: (id: string) => ['sources', id] as const,
  settings: ['settings'] as const,
}
```

### 1.2 Notes API (`lib/api/notes.ts`)

```typescript
import apiClient from './client'
import { NoteResponse, CreateNoteRequest } from '@/lib/types/api'

export const notesApi = {
  list: async (params?: { notebook_id?: string }) => {
    const response = await apiClient.get<NoteResponse[]>('/notes', { params })
    return response.data
  },

  get: async (id: string) => {
    const response = await apiClient.get<NoteResponse>(`/notes/${id}`)
    return response.data
  },

  create: async (data: CreateNoteRequest) => {
    const response = await apiClient.post<NoteResponse>('/notes', data)
    return response.data
  },

  update: async (id: string, data: Partial<CreateNoteRequest>) => {
    const response = await apiClient.put<NoteResponse>(`/notes/${id}`, data)
    return response.data
  },

  delete: async (id: string) => {
    await apiClient.delete(`/notes/${id}`)
  }
}
```

### 1.3 Sources API (`lib/api/sources.ts`)

```typescript
import apiClient from './client'
import { SourceListResponse } from '@/lib/types/api'

export interface CreateSourceRequest {
  notebook_id: string
  type: 'link' | 'upload' | 'text'
  url?: string
  file_path?: string
  content?: string
  title?: string
}

export const sourcesApi = {
  list: async (params?: { notebook_id?: string }) => {
    const response = await apiClient.get<SourceListResponse[]>('/sources', { params })
    return response.data
  },

  get: async (id: string) => {
    const response = await apiClient.get<SourceListResponse>(`/sources/${id}`)
    return response.data
  },

  create: async (data: CreateSourceRequest) => {
    const response = await apiClient.post<SourceListResponse>('/sources', data)
    return response.data
  },

  update: async (id: string, data: Partial<CreateSourceRequest>) => {
    const response = await apiClient.put<SourceListResponse>(`/sources/${id}`, data)
    return response.data
  },

  delete: async (id: string) => {
    await apiClient.delete(`/sources/${id}`)
  },

  upload: async (file: File, notebook_id: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('notebook_id', notebook_id)
    formData.append('type', 'upload')
    
    const response = await apiClient.post<SourceListResponse>('/sources', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  }
}
```

### 1.4 Custom Hooks

#### Notebooks Hook (`lib/hooks/use-notebooks.ts`)

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { notebooksApi } from '@/lib/api/notebooks'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { CreateNotebookRequest, UpdateNotebookRequest } from '@/lib/types/api'

export function useNotebooks(archived?: boolean) {
  return useQuery({
    queryKey: [...QUERY_KEYS.notebooks, { archived }],
    queryFn: () => notebooksApi.list({ archived, order_by: 'updated desc' }),
  })
}

export function useNotebook(id: string) {
  return useQuery({
    queryKey: QUERY_KEYS.notebook(id),
    queryFn: () => notebooksApi.get(id),
    enabled: !!id,
  })
}

export function useCreateNotebook() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (data: CreateNotebookRequest) => notebooksApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.notebooks })
      toast({
        title: 'Success',
        description: 'Notebook created successfully',
      })
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to create notebook',
        variant: 'destructive',
      })
    },
  })
}

export function useUpdateNotebook() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateNotebookRequest }) =>
      notebooksApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.notebooks })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.notebook(id) })
      toast({
        title: 'Success',
        description: 'Notebook updated successfully',
      })
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to update notebook',
        variant: 'destructive',
      })
    },
  })
}

export function useDeleteNotebook() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (id: string) => notebooksApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.notebooks })
      toast({
        title: 'Success',
        description: 'Notebook deleted successfully',
      })
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to delete notebook',
        variant: 'destructive',
      })
    },
  })
}
```

#### Sources Hook (`lib/hooks/use-sources.ts`)

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { sourcesApi, CreateSourceRequest } from '@/lib/api/sources'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'

export function useSources(notebookId?: string) {
  return useQuery({
    queryKey: QUERY_KEYS.sources(notebookId),
    queryFn: () => sourcesApi.list({ notebook_id: notebookId }),
    enabled: !!notebookId,
  })
}

export function useCreateSource() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (data: CreateSourceRequest) => sourcesApi.create(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ 
        queryKey: QUERY_KEYS.sources(variables.notebook_id) 
      })
      toast({
        title: 'Success',
        description: 'Source added successfully',
      })
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to add source',
        variant: 'destructive',
      })
    },
  })
}

export function useFileUpload() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ file, notebookId }: { file: File; notebookId: string }) =>
      sourcesApi.upload(file, notebookId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ 
        queryKey: QUERY_KEYS.sources(variables.notebookId) 
      })
      toast({
        title: 'Success',
        description: 'File uploaded successfully',
      })
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to upload file',
        variant: 'destructive',
      })
    },
  })
}
```

#### Notes Hook (`lib/hooks/use-notes.ts`)

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { notesApi } from '@/lib/api/notes'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { CreateNoteRequest } from '@/lib/types/api'

export function useNotes(notebookId?: string) {
  return useQuery({
    queryKey: QUERY_KEYS.notes(notebookId),
    queryFn: () => notesApi.list({ notebook_id: notebookId }),
    enabled: !!notebookId,
  })
}

export function useCreateNote() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (data: CreateNoteRequest) => notesApi.create(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ 
        queryKey: QUERY_KEYS.notes(variables.notebook_id) 
      })
      toast({
        title: 'Success',
        description: 'Note created successfully',
      })
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to create note',
        variant: 'destructive',
      })
    },
  })
}
```

---

## 2. Notebooks Page Implementation

### 2.1 Main Notebooks Page (`app/(dashboard)/notebooks/page.tsx`)

```typescript
'use client'

import { useState } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { NotebookList } from './components/NotebookList'
import { CreateNotebookForm } from './components/CreateNotebookForm'
import { Button } from '@/components/ui/button'
import { Plus } from 'lucide-react'
import { useNotebooks } from '@/lib/hooks/use-notebooks'

export default function NotebooksPage() {
  const [showCreateForm, setShowCreateForm] = useState(false)
  const { data: notebooks, isLoading, refetch } = useNotebooks(false)
  const { data: archivedNotebooks } = useNotebooks(true)

  return (
    <AppShell 
      title="Notebooks" 
      onRefresh={() => refetch()}
      headerActions={
        <Button onClick={() => setShowCreateForm(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Notebook
        </Button>
      }
    >
      <div className="space-y-8">
        {showCreateForm && (
          <CreateNotebookForm onClose={() => setShowCreateForm(false)} />
        )}
        
        <NotebookList 
          notebooks={notebooks} 
          isLoading={isLoading}
          title="Active Notebooks"
        />
        
        {archivedNotebooks && archivedNotebooks.length > 0 && (
          <NotebookList 
            notebooks={archivedNotebooks} 
            isLoading={false}
            title="Archived Notebooks"
            collapsible
          />
        )}
      </div>
    </AppShell>
  )
}
```

### 2.2 Individual Notebook Page (`app/(dashboard)/notebooks/[id]/page.tsx`)

```typescript
'use client'

import { useParams } from 'next/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { NotebookHeader } from '../components/NotebookHeader'
import { SourcesColumn } from '../components/SourcesColumn'
import { NotesColumn } from '../components/NotesColumn'
import { ChatColumn } from '../components/ChatColumn'
import { useNotebook } from '@/lib/hooks/use-notebooks'
import { useSources } from '@/lib/hooks/use-sources'
import { useNotes } from '@/lib/hooks/use-notes'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'

export default function NotebookPage() {
  const params = useParams()
  const notebookId = params.id as string

  const { data: notebook, isLoading: notebookLoading, refetch } = useNotebook(notebookId)
  const { data: sources, isLoading: sourcesLoading } = useSources(notebookId)
  const { data: notes, isLoading: notesLoading } = useNotes(notebookId)

  if (notebookLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!notebook) {
    return (
      <AppShell title="Notebook Not Found">
        <div className="text-center py-12">
          <p className="text-gray-500">Notebook not found</p>
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell 
      title={notebook.name} 
      onRefresh={() => refetch()}
    >
      <div className="space-y-6">
        <NotebookHeader notebook={notebook} />
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-12rem)]">
          <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-6">
            <SourcesColumn 
              sources={sources} 
              isLoading={sourcesLoading}
              notebookId={notebookId}
            />
            <NotesColumn 
              notes={notes} 
              isLoading={notesLoading}
              notebookId={notebookId}
            />
          </div>
          
          <ChatColumn notebookId={notebookId} />
        </div>
      </div>
    </AppShell>
  )
}
```

### 2.3 Notebook Components

#### Notebook List (`app/(dashboard)/notebooks/components/NotebookList.tsx`)

```typescript
'use client'

import { NotebookResponse } from '@/lib/types/api'
import { NotebookCard } from './NotebookCard'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'
import { Book, ChevronDown, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useState } from 'react'

interface NotebookListProps {
  notebooks?: NotebookResponse[]
  isLoading: boolean
  title: string
  collapsible?: boolean
}

export function NotebookList({ 
  notebooks, 
  isLoading, 
  title, 
  collapsible = false 
}: NotebookListProps) {
  const [isExpanded, setIsExpanded] = useState(!collapsible)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!notebooks || notebooks.length === 0) {
    return (
      <EmptyState
        icon={Book}
        title={`No ${title.toLowerCase()}`}
        description="Start by creating your first notebook to organize your research."
      />
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        {collapsible && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </Button>
        )}
        <h2 className="text-lg font-semibold">{title}</h2>
        <span className="text-sm text-gray-500">({notebooks.length})</span>
      </div>

      {isExpanded && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {notebooks.map((notebook) => (
            <NotebookCard key={notebook.id} notebook={notebook} />
          ))}
        </div>
      )}
    </div>
  )
}
```

#### Notebook Card (`app/(dashboard)/notebooks/components/NotebookCard.tsx`)

```typescript
'use client'

import Link from 'next/link'
import { NotebookResponse } from '@/lib/types/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { MoreHorizontal, Archive, ArchiveRestore, Trash2, Edit } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useUpdateNotebook, useDeleteNotebook } from '@/lib/hooks/use-notebooks'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { useState } from 'react'

interface NotebookCardProps {
  notebook: NotebookResponse
}

export function NotebookCard({ notebook }: NotebookCardProps) {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const updateNotebook = useUpdateNotebook()
  const deleteNotebook = useDeleteNotebook()

  const handleArchiveToggle = () => {
    updateNotebook.mutate({
      id: notebook.id,
      data: { archived: !notebook.archived }
    })
  }

  const handleDelete = () => {
    deleteNotebook.mutate(notebook.id)
    setShowDeleteDialog(false)
  }

  return (
    <>
      <Card className="group hover:shadow-md transition-shadow">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <CardTitle className="text-base truncate">
                <Link 
                  href={`/notebooks/${notebook.id}`}
                  className="hover:text-blue-600 transition-colors"
                >
                  {notebook.name}
                </Link>
              </CardTitle>
              {notebook.archived && (
                <Badge variant="secondary" className="mt-1">
                  Archived
                </Badge>
              )}
            </div>
            
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={handleArchiveToggle}>
                  {notebook.archived ? (
                    <>
                      <ArchiveRestore className="h-4 w-4 mr-2" />
                      Unarchive
                    </>
                  ) : (
                    <>
                      <Archive className="h-4 w-4 mr-2" />
                      Archive
                    </>
                  )}
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => setShowDeleteDialog(true)}
                  className="text-red-600"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </CardHeader>
        
        <CardContent>
          <CardDescription className="line-clamp-2 text-sm">
            {notebook.description || 'No description'}
          </CardDescription>
          
          <div className="mt-3 text-xs text-gray-500">
            Updated {formatDistanceToNow(new Date(notebook.updated), { addSuffix: true })}
          </div>
        </CardContent>
      </Card>

      <ConfirmDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        title="Delete Notebook"
        description={`Are you sure you want to delete "${notebook.name}"? This action cannot be undone and will delete all sources, notes, and chat sessions.`}
        confirmText="Delete"
        confirmVariant="destructive"
        onConfirm={handleDelete}
      />
    </>
  )
}
```

#### Create Notebook Form (`app/(dashboard)/notebooks/components/CreateNotebookForm.tsx`)

```typescript
'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { X } from 'lucide-react'
import { useCreateNotebook } from '@/lib/hooks/use-notebooks'
import { CreateNotebookRequest } from '@/lib/types/api'

interface CreateNotebookFormProps {
  onClose: () => void
}

export function CreateNotebookForm({ onClose }: CreateNotebookFormProps) {
  const createNotebook = useCreateNotebook()
  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
    reset
  } = useForm<CreateNotebookRequest>()

  const onSubmit = async (data: CreateNotebookRequest) => {
    await createNotebook.mutateAsync(data)
    reset()
    onClose()
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Create New Notebook</CardTitle>
            <CardDescription>
              Start organizing your research with a new notebook
            </CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <Label htmlFor="name">Name *</Label>
            <Input
              id="name"
              {...register('name', { 
                required: 'Name is required',
                minLength: { value: 1, message: 'Name cannot be empty' }
              })}
              placeholder="Enter notebook name"
            />
            {errors.name && (
              <p className="text-sm text-red-600 mt-1">{errors.name.message}</p>
            )}
          </div>
          
          <div>
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              {...register('description')}
              placeholder="Describe the purpose and scope of this notebook..."
              rows={3}
            />
          </div>
          
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button 
              type="submit" 
              disabled={!isValid || createNotebook.isPending}
            >
              {createNotebook.isPending ? 'Creating...' : 'Create Notebook'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
```

#### Notebook Header (`app/(dashboard)/notebooks/components/NotebookHeader.tsx`)

```typescript
'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { NotebookResponse } from '@/lib/types/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Edit3, Save, X, Archive, ArchiveRestore, Trash2 } from 'lucide-react'
import { useUpdateNotebook, useDeleteNotebook } from '@/lib/hooks/use-notebooks'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { formatDistanceToNow } from 'date-fns'

interface NotebookHeaderProps {
  notebook: NotebookResponse
}

export function NotebookHeader({ notebook }: NotebookHeaderProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  
  const updateNotebook = useUpdateNotebook()
  const deleteNotebook = useDeleteNotebook()
  
  const { register, handleSubmit, reset } = useForm({
    defaultValues: {
      name: notebook.name,
      description: notebook.description || ''
    }
  })

  const handleSave = async (data: { name: string; description: string }) => {
    await updateNotebook.mutateAsync({
      id: notebook.id,
      data: {
        name: data.name,
        description: data.description || undefined
      }
    })
    setIsEditing(false)
  }

  const handleCancel = () => {
    reset()
    setIsEditing(false)
  }

  const handleArchiveToggle = () => {
    updateNotebook.mutate({
      id: notebook.id,
      data: { archived: !notebook.archived }
    })
  }

  const handleDelete = () => {
    deleteNotebook.mutate(notebook.id)
    setShowDeleteDialog(false)
  }

  return (
    <>
      <div className="border-b pb-6">
        {isEditing ? (
          <form onSubmit={handleSubmit(handleSave)} className="space-y-4">
            <div>
              <Input
                {...register('name', { required: true })}
                className="text-2xl font-bold border-none px-0 shadow-none focus-visible:ring-0"
              />
            </div>
            <div>
              <Textarea
                {...register('description')}
                placeholder="Add a description for this notebook..."
                rows={2}
                className="border-none px-0 shadow-none focus-visible:ring-0"
              />
            </div>
            <div className="flex gap-2">
              <Button type="submit" size="sm">
                <Save className="h-4 w-4 mr-2" />
                Save
              </Button>
              <Button type="button" variant="outline" size="sm" onClick={handleCancel}>
                <X className="h-4 w-4 mr-2" />
                Cancel
              </Button>
            </div>
          </form>
        ) : (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold">{notebook.name}</h1>
                {notebook.archived && (
                  <Badge variant="secondary">Archived</Badge>
                )}
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsEditing(true)}
                >
                  <Edit3 className="h-4 w-4 mr-2" />
                  Edit
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleArchiveToggle}
                >
                  {notebook.archived ? (
                    <>
                      <ArchiveRestore className="h-4 w-4 mr-2" />
                      Unarchive
                    </>
                  ) : (
                    <>
                      <Archive className="h-4 w-4 mr-2" />
                      Archive
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowDeleteDialog(true)}
                  className="text-red-600 hover:text-red-700"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </Button>
              </div>
            </div>
            
            {notebook.description && (
              <p className="text-gray-600">{notebook.description}</p>
            )}
            
            <div className="text-sm text-gray-500">
              Created {formatDistanceToNow(new Date(notebook.created), { addSuffix: true })} • 
              Updated {formatDistanceToNow(new Date(notebook.updated), { addSuffix: true })}
            </div>
          </div>
        )}
      </div>

      <ConfirmDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        title="Delete Notebook"
        description={`Are you sure you want to delete "${notebook.name}"? This action cannot be undone and will delete all sources, notes, and chat sessions.`}
        confirmText="Delete Forever"
        confirmVariant="destructive"
        onConfirm={handleDelete}
      />
    </>
  )
}
```

---

## 3. Three-Column Layout Components

### 3.1 Sources Column (`app/(dashboard)/notebooks/components/SourcesColumn.tsx`)

```typescript
'use client'

import { useState } from 'react'
import { SourceListResponse } from '@/lib/types/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Plus, FileText } from 'lucide-react'
import { SourceCard } from './SourceCard'
import { AddSourceDialog } from './AddSourceDialog'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'

interface SourcesColumnProps {
  sources?: SourceListResponse[]
  isLoading: boolean
  notebookId: string
}

export function SourcesColumn({ sources, isLoading, notebookId }: SourcesColumnProps) {
  const [showAddDialog, setShowAddDialog] = useState(false)

  return (
    <>
      <Card className="h-full flex flex-col">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Sources</CardTitle>
            <Button
              size="sm"
              onClick={() => setShowAddDialog(true)}
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Source
            </Button>
          </div>
        </CardHeader>
        
        <CardContent className="flex-1 overflow-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <LoadingSpinner />
            </div>
          ) : !sources || sources.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="No sources yet"
              description="Add your first source to start building your knowledge base."
            />
          ) : (
            <div className="space-y-3">
              {sources.map((source) => (
                <SourceCard key={source.id} source={source} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <AddSourceDialog
        open={showAddDialog}
        onOpenChange={setShowAddDialog}
        notebookId={notebookId}
      />
    </>
  )
}
```

### 3.2 Notes Column (`app/(dashboard)/notebooks/components/NotesColumn.tsx`)

```typescript
'use client'

import { useState } from 'react'
import { NoteResponse } from '@/lib/types/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Plus, StickyNote } from 'lucide-react'
import { NoteCard } from './NoteCard'
import { AddNoteDialog } from './AddNoteDialog'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'

interface NotesColumnProps {
  notes?: NoteResponse[]
  isLoading: boolean
  notebookId: string
}

export function NotesColumn({ notes, isLoading, notebookId }: NotesColumnProps) {
  const [showAddDialog, setShowAddDialog] = useState(false)

  return (
    <>
      <Card className="h-full flex flex-col">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Notes</CardTitle>
            <Button
              size="sm"
              onClick={() => setShowAddDialog(true)}
            >
              <Plus className="h-4 w-4 mr-2" />
              Write Note
            </Button>
          </div>
        </CardHeader>
        
        <CardContent className="flex-1 overflow-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <LoadingSpinner />
            </div>
          ) : !notes || notes.length === 0 ? (
            <EmptyState
              icon={StickyNote}
              title="No notes yet"
              description="Create your first note to capture insights and observations."
            />
          ) : (
            <div className="space-y-3">
              {notes.map((note) => (
                <NoteCard key={note.id} note={note} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <AddNoteDialog
        open={showAddDialog}
        onOpenChange={setShowAddDialog}
        notebookId={notebookId}
      />
    </>
  )
}
```

### 3.3 Chat Column (`app/(dashboard)/notebooks/components/ChatColumn.tsx`)

```typescript
'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { MessageCircle } from 'lucide-react'

interface ChatColumnProps {
  notebookId: string
}

export function ChatColumn({ notebookId }: ChatColumnProps) {
  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Chat</CardTitle>
          <Badge variant="secondary">Phase 3</Badge>
        </div>
      </CardHeader>
      
      <CardContent className="flex-1 flex items-center justify-center">
        <div className="text-center text-gray-500">
          <MessageCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>Chat interface coming in Phase 3</p>
        </div>
      </CardContent>
    </Card>
  )
}
```

---

## 4. Settings Page Implementation

### 4.1 Settings Page (`app/(dashboard)/settings/page.tsx`)

```typescript
'use client'

import { AppShell } from '@/components/layout/AppShell'
import { SettingsForm } from './components/SettingsForm'
import { useSettings } from '@/lib/hooks/use-settings'

export default function SettingsPage() {
  const { refetch } = useSettings()

  return (
    <AppShell title="Settings" onRefresh={() => refetch()}>
      <div className="max-w-4xl">
        <SettingsForm />
      </div>
    </AppShell>
  )
}
```

### 4.2 Settings Hook (`lib/hooks/use-settings.ts`)

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { settingsApi } from '@/lib/api/settings'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { SettingsResponse } from '@/lib/types/api'

export function useSettings() {
  return useQuery({
    queryKey: QUERY_KEYS.settings,
    queryFn: () => settingsApi.get(),
  })
}

export function useUpdateSettings() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (data: Partial<SettingsResponse>) => settingsApi.update(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.settings })
      toast({
        title: 'Success',
        description: 'Settings updated successfully',
      })
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to update settings',
        variant: 'destructive',
      })
    },
  })
}
```

---

## 5. Common Components

### 5.1 Confirm Dialog (`components/common/ConfirmDialog.tsx`)

```typescript
'use client'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'

interface ConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description: string
  confirmText?: string
  confirmVariant?: 'default' | 'destructive'
  onConfirm: () => void
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmText = 'Confirm',
  confirmVariant = 'default',
  onConfirm,
}: ConfirmDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            className={confirmVariant === 'destructive' ? 'bg-red-600 hover:bg-red-700' : ''}
          >
            {confirmText}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
```

### 5.2 Empty State (`components/common/EmptyState.tsx`)

```typescript
import { LucideIcon } from 'lucide-react'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description: string
  action?: React.ReactNode
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="text-center py-12">
      <Icon className="h-12 w-12 mx-auto text-gray-400 mb-4" />
      <h3 className="text-lg font-medium text-gray-900 mb-2">{title}</h3>
      <p className="text-gray-500 mb-4">{description}</p>
      {action}
    </div>
  )
}
```

---

## 6. Additional Dependencies

Add to package.json:

```json
{
  "dependencies": {
    "@tanstack/react-query": "^5.0.0",
    "react-hook-form": "^7.48.0",
    "@hookform/resolvers": "^3.3.0",
    "zod": "^3.22.0",
    "date-fns": "^2.30.0",
    "react-markdown": "^9.0.0",
    "@monaco-editor/react": "^4.6.0"
  }
}
```

---

## Success Criteria

Phase 2 is complete when:

1. ✅ **Notebooks List**: Display, create, edit, archive, delete notebooks
2. ✅ **Individual Notebook View**: Three-column layout with sources, notes, and chat placeholder
3. ✅ **Source Management**: Add, display, and manage sources (basic functionality - full implementation in Phase 3)
4. ✅ **Note Management**: Create, display, and manage notes (basic functionality - full implementation in Phase 3)
5. ✅ **Settings Page**: Complete settings form with dropdown selects and proper validation
6. ✅ **Data Management**: React Query integration with proper caching and error handling
7. ✅ **Error Handling**: Comprehensive error handling and user feedback
8. ✅ **Loading States**: Proper loading states throughout the application
9. ✅ **UI Components**: Enhanced components (dialogs, empty states, badges, collapsibles)
10. ✅ **Form Handling**: React Hook Form integration with proper validation

## 🎉 **PHASE 2 COMPLETED SUCCESSFULLY!**

**Key Accomplishments:**
- ✅ Complete notebooks CRUD functionality with archive/unarchive
- ✅ Three-column responsive layout with sources, notes, and chat placeholder
- ✅ Comprehensive settings page with dropdown selects and help tooltips
- ✅ React Query integration for robust data management
- ✅ Enhanced UI with proper loading states, error handling, and empty states
- ✅ Form validation using React Hook Form and Zod
- ✅ Proper TypeScript integration throughout
- ✅ Fixed dropdown pre-selection issue with React Hook Form + Radix UI integration

**Items Moved to Phase 3:**
- Advanced source management (file upload, drag & drop, full text content)
- Advanced note management (markdown editing, rich text features)
- Full chat implementation with AI integration
- Search and AI querying functionality
- Real-time streaming responses

This phase successfully establishes the core user interface and data management patterns that Phase 3 will extend with advanced AI-powered features.