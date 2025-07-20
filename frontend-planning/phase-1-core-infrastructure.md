# Phase 1: Core Infrastructure Implementation Guide

## Overview

Phase 1 establishes the foundational architecture for the React/Shadcn migration, including authentication, navigation, routing, and API integration. This phase creates the core infrastructure that all subsequent phases will build upon.

## Technology Stack

- **Framework**: Next.js 14+ with App Router
- **UI Library**: Shadcn/UI components
- **Styling**: Tailwind CSS
- **State Management**: Zustand for global state, React Query for server state
- **HTTP Client**: Axios with interceptors
- **Authentication**: Bearer token with localStorage
- **Routing**: Next.js App Router with middleware

## Project Structure

```
src/
├── app/
│   ├── (auth)/
│   │   └── login/
│   │       └── page.tsx
│   ├── (dashboard)/
│   │   ├── layout.tsx
│   │   ├── page.tsx           # Dashboard redirect
│   │   ├── notebooks/
│   │   │   └── page.tsx
│   │   ├── search/
│   │   │   └── page.tsx
│   │   ├── podcasts/
│   │   │   └── page.tsx
│   │   ├── models/
│   │   │   └── page.tsx
│   │   ├── transformations/
│   │   │   └── page.tsx
│   │   └── settings/
│   │       └── page.tsx
│   ├── globals.css
│   ├── layout.tsx
│   └── middleware.ts
├── components/
│   ├── ui/                    # Shadcn components
│   ├── layout/
│   │   ├── AppSidebar.tsx
│   │   ├── AppHeader.tsx
│   │   └── AppShell.tsx
│   ├── auth/
│   │   └── LoginForm.tsx
│   └── common/
│       ├── LoadingSpinner.tsx
│       ├── ErrorBoundary.tsx
│       └── Toast.tsx
├── lib/
│   ├── api/
│   │   ├── client.ts
│   │   ├── auth.ts
│   │   ├── notebooks.ts
│   │   ├── notes.ts
│   │   ├── sources.ts
│   │   └── settings.ts
│   ├── stores/
│   │   ├── auth-store.ts
│   │   └── app-store.ts
│   ├── hooks/
│   │   ├── use-auth.ts
│   │   ├── use-api.ts
│   │   └── use-toast.ts
│   ├── types/
│   │   ├── api.ts
│   │   ├── auth.ts
│   │   └── common.ts
│   └── utils.ts
└── middleware.ts
```

---

## 1. Authentication System

### 1.1 Authentication Store (`lib/stores/auth-store.ts`)

```typescript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  isAuthenticated: boolean
  token: string | null
  isLoading: boolean
  error: string | null
  login: (password: string) => Promise<boolean>
  logout: () => void
  checkAuth: () => Promise<boolean>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      isAuthenticated: false,
      token: null,
      isLoading: false,
      error: null,
      
      login: async (password: string) => {
        set({ isLoading: true, error: null })
        try {
          // Test auth with API call
          const response = await fetch('/api/notebooks', {
            headers: {
              'Authorization': `Bearer ${password}`
            }
          })
          
          if (response.ok) {
            set({ 
              isAuthenticated: true, 
              token: password, 
              isLoading: false 
            })
            return true
          } else {
            set({ 
              error: 'Invalid password', 
              isLoading: false 
            })
            return false
          }
        } catch (error) {
          set({ 
            error: 'Authentication failed', 
            isLoading: false 
          })
          return false
        }
      },
      
      logout: () => {
        set({ 
          isAuthenticated: false, 
          token: null, 
          error: null 
        })
      },
      
      checkAuth: async () => {
        const { token } = get()
        if (!token) return false
        
        try {
          const response = await fetch('/api/health', {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          })
          
          if (response.ok) {
            set({ isAuthenticated: true })
            return true
          } else {
            set({ isAuthenticated: false, token: null })
            return false
          }
        } catch {
          set({ isAuthenticated: false, token: null })
          return false
        }
      }
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ 
        token: state.token,
        isAuthenticated: state.isAuthenticated 
      })
    }
  )
)
```

### 1.2 Authentication Hook (`lib/hooks/use-auth.ts`)

```typescript
import { useAuthStore } from '@/lib/stores/auth-store'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'

export function useAuth() {
  const router = useRouter()
  const { 
    isAuthenticated, 
    isLoading, 
    login, 
    logout, 
    checkAuth,
    error 
  } = useAuthStore()

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  const handleLogin = async (password: string) => {
    const success = await login(password)
    if (success) {
      router.push('/notebooks')
    }
    return success
  }

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  return {
    isAuthenticated,
    isLoading,
    error,
    login: handleLogin,
    logout: handleLogout
  }
}
```

### 1.3 Login Form Component (`components/auth/LoginForm.tsx`)

```typescript
'use client'

import { useState } from 'react'
import { useAuth } from '@/lib/hooks/use-auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertCircle } from 'lucide-react'

export function LoginForm() {
  const [password, setPassword] = useState('')
  const { login, isLoading, error } = useAuth()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password.trim()) {
      await login(password)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle>Open Notebook</CardTitle>
          <CardDescription>
            Enter your password to access the application
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoading}
              />
            </div>
            
            {error && (
              <div className="flex items-center gap-2 text-red-600 text-sm">
                <AlertCircle className="h-4 w-4" />
                {error}
              </div>
            )}
            
            <Button 
              type="submit" 
              className="w-full" 
              disabled={isLoading || !password.trim()}
            >
              {isLoading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
```

### 1.4 Login Page (`app/(auth)/login/page.tsx`)

```typescript
import { LoginForm } from '@/components/auth/LoginForm'

export default function LoginPage() {
  return <LoginForm />
}
```

---

## 2. API Integration Layer

### 2.1 API Client (`lib/api/client.ts`)

```typescript
import axios, { AxiosResponse } from 'axios'
import { useAuthStore } from '@/lib/stores/auth-store'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5055'

export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth header
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default apiClient
```

### 2.2 API Types (`lib/types/api.ts`)

```typescript
export interface NotebookResponse {
  id: string
  name: string
  description: string
  archived: boolean
  created: string
  updated: string
}

export interface NoteResponse {
  id: string
  title: string | null
  content: string | null
  note_type: string | null
  created: string
  updated: string
}

export interface SourceListResponse {
  id: string
  title: string | null
  topics: string[]
  asset: {
    file_path?: string
    url?: string
  } | null
  embedded_chunks: number
  insights_count: number
  created: string
  updated: string
}

export interface SettingsResponse {
  default_content_processing_engine_doc?: string
  default_content_processing_engine_url?: string
  default_embedding_option?: string
  auto_delete_files?: string
  youtube_preferred_languages?: string[]
}

export interface CreateNotebookRequest {
  name: string
  description?: string
}

export interface UpdateNotebookRequest {
  name?: string
  description?: string
  archived?: boolean
}

export interface CreateNoteRequest {
  title?: string
  content: string
  note_type?: string
  notebook_id?: string
}

export interface APIError {
  detail: string
}
```

### 2.3 Notebooks API (`lib/api/notebooks.ts`)

```typescript
import apiClient from './client'
import { NotebookResponse, CreateNotebookRequest, UpdateNotebookRequest } from '@/lib/types/api'

export const notebooksApi = {
  list: async (params?: { archived?: boolean; order_by?: string }) => {
    const response = await apiClient.get<NotebookResponse[]>('/notebooks', { params })
    return response.data
  },

  get: async (id: string) => {
    const response = await apiClient.get<NotebookResponse>(`/notebooks/${id}`)
    return response.data
  },

  create: async (data: CreateNotebookRequest) => {
    const response = await apiClient.post<NotebookResponse>('/notebooks', data)
    return response.data
  },

  update: async (id: string, data: UpdateNotebookRequest) => {
    const response = await apiClient.put<NotebookResponse>(`/notebooks/${id}`, data)
    return response.data
  },

  delete: async (id: string) => {
    await apiClient.delete(`/notebooks/${id}`)
  }
}
```

### 2.4 Settings API (`lib/api/settings.ts`)

```typescript
import apiClient from './client'
import { SettingsResponse } from '@/lib/types/api'

export const settingsApi = {
  get: async () => {
    const response = await apiClient.get<SettingsResponse>('/settings')
    return response.data
  },

  update: async (data: Partial<SettingsResponse>) => {
    const response = await apiClient.put<SettingsResponse>('/settings', data)
    return response.data
  }
}
```

---

## 3. Navigation and Layout

### 3.1 App Sidebar (`components/layout/AppSidebar.tsx`)

```typescript
'use client'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { 
  Book, 
  Search, 
  Mic, 
  Bot, 
  Shuffle, 
  Settings,
  LogOut
} from 'lucide-react'
import { useAuth } from '@/lib/hooks/use-auth'

const navigation = [
  { name: 'Notebooks', href: '/notebooks', icon: Book },
  { name: 'Ask and Search', href: '/search', icon: Search },
  { name: 'Podcasts', href: '/podcasts', icon: Mic },
  { name: 'Models', href: '/models', icon: Bot },
  { name: 'Transformations', href: '/transformations', icon: Shuffle },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export function AppSidebar() {
  const pathname = usePathname()
  const { logout } = useAuth()

  return (
    <div className="flex h-full w-64 flex-col bg-gray-50 border-r">
      <div className="flex h-16 items-center px-6">
        <h1 className="text-lg font-semibold">Open Notebook</h1>
      </div>
      
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navigation.map((item) => {
          const isActive = pathname.startsWith(item.href)
          return (
            <Link key={item.name} href={item.href}>
              <Button
                variant={isActive ? "secondary" : "ghost"}
                className={cn(
                  "w-full justify-start gap-3",
                  isActive && "bg-gray-200"
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.name}
              </Button>
            </Link>
          )
        })}
      </nav>
      
      <div className="p-3">
        <Button 
          variant="outline" 
          className="w-full justify-start gap-3"
          onClick={logout}
        >
          <LogOut className="h-4 w-4" />
          Sign Out
        </Button>
      </div>
    </div>
  )
}
```

### 3.2 App Header (`components/layout/AppHeader.tsx`)

```typescript
'use client'

import { Button } from '@/components/ui/button'
import { RefreshCw } from 'lucide-react'

interface AppHeaderProps {
  title: string
  onRefresh?: () => void
  children?: React.ReactNode
}

export function AppHeader({ title, onRefresh, children }: AppHeaderProps) {
  return (
    <div className="flex h-16 items-center justify-between border-b px-6">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-semibold">{title}</h1>
        {onRefresh && (
          <Button variant="outline" size="sm" onClick={onRefresh}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        )}
      </div>
      {children && (
        <div className="flex items-center gap-2">
          {children}
        </div>
      )}
    </div>
  )
}
```

### 3.3 App Shell (`components/layout/AppShell.tsx`)

```typescript
'use client'

import { AppSidebar } from './AppSidebar'
import { AppHeader } from './AppHeader'

interface AppShellProps {
  title: string
  onRefresh?: () => void
  headerActions?: React.ReactNode
  children: React.ReactNode
}

export function AppShell({ title, onRefresh, headerActions, children }: AppShellProps) {
  return (
    <div className="flex h-screen">
      <AppSidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <AppHeader title={title} onRefresh={onRefresh}>
          {headerActions}
        </AppHeader>
        <main className="flex-1 overflow-auto p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
```

### 3.4 Dashboard Layout (`app/(dashboard)/layout.tsx`)

```typescript
'use client'

import { useAuth } from '@/lib/hooks/use-auth'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { isAuthenticated, isLoading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, isLoading, router])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner />
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return <>{children}</>
}
```

---

## 4. Routing and Middleware

### 4.1 Middleware (`middleware.ts`)

```typescript
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Redirect root to notebooks
  if (pathname === '/') {
    return NextResponse.redirect(new URL('/notebooks', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
}
```

### 4.2 Main Layout (`app/layout.tsx`)

```typescript
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Toaster } from '@/components/ui/toaster'
import { ErrorBoundary } from '@/components/common/ErrorBoundary'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Open Notebook',
  description: 'Privacy-focused research and knowledge management',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <ErrorBoundary>
          {children}
        </ErrorBoundary>
        <Toaster />
      </body>
    </html>
  )
}
```

### 4.3 Dashboard Home (`app/(dashboard)/page.tsx`)

```typescript
import { redirect } from 'next/navigation'

export default function DashboardPage() {
  redirect('/notebooks')
}
```

---

## 5. Common Components

### 5.1 Loading Spinner (`components/common/LoadingSpinner.tsx`)

```typescript
import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface LoadingSpinnerProps {
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

export function LoadingSpinner({ className, size = 'md' }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-6 w-6',
    lg: 'h-8 w-8'
  }

  return (
    <Loader2 className={cn('animate-spin', sizeClasses[size], className)} />
  )
}
```

### 5.2 Error Boundary (`components/common/ErrorBoundary.tsx`)

```typescript
'use client'

import React from 'react'
import { AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ErrorBoundaryState {
  hasError: boolean
}

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  ErrorBoundaryState
> {
  constructor(props: { children: React.ReactNode }) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error boundary caught an error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center p-4">
          <div className="text-center">
            <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h1 className="text-xl font-semibold mb-2">Something went wrong</h1>
            <p className="text-gray-600 mb-4">
              An unexpected error occurred. Please try refreshing the page.
            </p>
            <Button onClick={() => window.location.reload()}>
              Refresh Page
            </Button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
```

---

## 6. Basic Page Skeletons

### 6.1 Notebooks Page (`app/(dashboard)/notebooks/page.tsx`)

```typescript
'use client'

import { AppShell } from '@/components/layout/AppShell'

export default function NotebooksPage() {
  return (
    <AppShell title="Notebooks">
      <div className="space-y-6">
        <p className="text-gray-600">
          Notebooks page - Phase 2 implementation coming soon
        </p>
      </div>
    </AppShell>
  )
}
```

### 6.2 Settings Page (`app/(dashboard)/settings/page.tsx`)

```typescript
'use client'

import { AppShell } from '@/components/layout/AppShell'

export default function SettingsPage() {
  return (
    <AppShell title="Settings">
      <div className="space-y-6">
        <p className="text-gray-600">
          Settings page - Phase 2 implementation coming soon
        </p>
      </div>
    </AppShell>
  )
}
```

### 6.3 Other Page Skeletons

Create similar placeholder pages for:
- `app/(dashboard)/search/page.tsx`
- `app/(dashboard)/podcasts/page.tsx`
- `app/(dashboard)/models/page.tsx`
- `app/(dashboard)/transformations/page.tsx`

---

## 7. Setup Instructions

### 7.1 Dependencies

```json
{
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.0.0",
    "react-dom": "^18.0.0",
    "axios": "^1.6.0",
    "zustand": "^4.4.0",
    "@tanstack/react-query": "^5.0.0",
    "lucide-react": "^0.300.0",
    "tailwindcss": "^3.3.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.0.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/react": "^18.0.0",
    "@types/react-dom": "^18.0.0",
    "typescript": "^5.0.0"
  }
}
```

### 7.2 Environment Variables

```env
NEXT_PUBLIC_API_URL=http://localhost:5055
```

### 7.3 Shadcn/UI Setup

```bash
npx shadcn-ui@latest init
npx shadcn-ui@latest add button
npx shadcn-ui@latest add input
npx shadcn-ui@latest add card
npx shadcn-ui@latest add toast
npx shadcn-ui@latest add toaster
```

---

## 8. Testing Strategy

### 8.1 Unit Tests
- Authentication store functionality
- API client interceptors
- Component rendering

### 8.2 Integration Tests
- Login flow
- Navigation functionality
- API error handling

### 8.3 E2E Tests
- Complete authentication flow
- Navigation between pages
- Error boundary behavior

---

## Success Criteria

Phase 1 is complete when:

1. ✅ **Authentication System**: Users can log in with password protection
2. ✅ **Navigation**: Sidebar navigation works with route highlighting  
3. ✅ **Basic Layouts**: All pages have consistent layout structure
4. ✅ **API Integration**: Base API client with auth interceptors
5. ✅ **Error Handling**: Proper error boundaries and 401 handling
6. ✅ **State Management**: Auth state persists across sessions
7. ✅ **Responsive Design**: Works on desktop and mobile
8. ✅ **Loading States**: Proper loading indicators throughout

## Phase 1 Implementation Status: ✅ COMPLETED

### What Was Implemented:

#### ✅ Core Infrastructure
- **Next.js 14 Project**: Created with TypeScript, Tailwind CSS, and App Router
- **Shadcn/UI Setup**: Initialized with essential components (button, input, card, sonner, alert-dialog, dropdown-menu)
- **Project Structure**: Complete directory structure following the Phase 1 specification

#### ✅ Authentication System
- **Zustand Store**: `auth-store.ts` with persistent authentication state
- **Auth Hook**: `use-auth.ts` for React component integration  
- **Login Form**: Complete login interface with error handling
- **Bearer Token**: Working authentication with API integration
- **Route Protection**: Dashboard layout with authentication guards

#### ✅ API Integration Layer
- **Axios Client**: `client.ts` with request/response interceptors
- **Auth Interceptors**: Automatic token injection and 401 handling
- **API Modules**: `notebooks.ts` and `settings.ts` with type-safe endpoints
- **Error Handling**: Comprehensive error handling with user feedback

#### ✅ Navigation and Layout
- **App Sidebar**: Working navigation with route highlighting
- **App Header**: Header component with refresh and action buttons
- **App Shell**: Complete layout system combining sidebar and header
- **Route Protection**: Dashboard layout that redirects unauthenticated users

#### ✅ Page Structure
- **Login Page**: `/login` with complete authentication flow
- **Dashboard Pages**: All main pages (`/notebooks`, `/search`, `/podcasts`, `/models`, `/transformations`, `/settings`)
- **Route Redirects**: Root `/` redirects to `/notebooks`
- **Middleware**: Next.js middleware for route handling

#### ✅ Type Safety
- **API Types**: Complete TypeScript interfaces for all API responses
- **Auth Types**: Type-safe authentication state management
- **Component Props**: Fully typed component interfaces

#### ✅ Development Setup
- **Environment Variables**: `.env.local` configured for API URL
- **Dependencies**: All required packages installed and configured
- **Development Ready**: Application runs successfully with `npm run dev`

### Technical Implementation Details:

#### Authentication Flow:
1. User enters password on login page
2. Auth store tests API connectivity with multiple endpoints (/, /health, /api/notebooks)
3. On success, token is stored in localStorage via Zustand persistence
4. Dashboard layout checks authentication and redirects if needed
5. API client automatically injects Bearer token on all requests
6. 401 responses trigger automatic logout and redirect to login

#### Error Handling:
- Network errors display user-friendly messages
- API errors show specific HTTP status codes
- Authentication failures clear stored tokens
- Loading states prevent duplicate requests

#### Performance Features:
- Zustand state persistence for auth across browser sessions
- Axios interceptors for automatic token management
- Route-based code splitting with Next.js App Router
- Minimal initial bundle with only essential components

This foundation provides everything needed for Phase 2 implementation, with robust authentication, routing, and API integration fully functional.