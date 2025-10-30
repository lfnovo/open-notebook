# Open Notebook Feature Extension Plan

## Overview

This document outlines a comprehensive plan to extend Open Notebook with four major feature areas:
1. **Batch Upload Functionality** - Enable multiple file uploads simultaneously
2. **Third-Party Service Connections** - Expand integration capabilities beyond AI providers
3. **Enhanced Mobile Support** - Improve mobile responsiveness and touch interactions
4. **Advanced Message Rendering** - Rich chat interface with multimedia support and interactive elements

## Current State Analysis

### Existing Upload System
- **Single File Only**: Current implementation supports one file at a time
- **Backend**: `/api/sources/upload` endpoint in `api/routers/sources.py`
- **Frontend**: File input in `SourceTypeStep.tsx` component
- **Security**: Path validation, unique filename generation, file type validation
- **Processing**: Async/sync processing with background job queuing
- **Supported Formats**: PDF, DOC, DOCX, TXT, MD, EPUB

### Current Third-Party Integrations
- **AI Providers**: 16+ providers via Esperanto library abstraction
- **Database**: SurrealDB with flexible document schema
- **Content Processing**: Docling, Firecrawl, Jina, Simple processors
- **Background Jobs**: SurrealDB-backed command system
- **Plugin Architecture**: Extensible system with podcasts plugin example

### Current Mobile Support
- **Limited Responsiveness**: Desktop-first design with minimal mobile optimizations
- **Fixed Sidebar**: No responsive navigation for mobile screens
- **Breakpoints**: Basic Tailwind breakpoints (sm: 640px, md: 768px, lg: 1024px)
- **Touch Issues**: No mobile-specific touch interactions or feedback

---

## 1. Batch Upload Feature Implementation

### 1.1 Backend Implementation

#### API Endpoint Extensions

**New Endpoint**: `/api/sources/batch`
```python
@router.post("/sources/batch", response_model=List[SourceResponse])
async def create_batch_sources(
    files: List[UploadFile] = File(...),
    notebook_id: Optional[str] = Form(None),
    notebooks: Optional[str] = Form(None),
    transformations: Optional[str] = Form(None),
    embed: str = Form("false"),
    async_processing: str = Form("true"),
    batch_name: Optional[str] = Form(None)
):
```

**Key Features**:
- Accept multiple files in single request
- Optional batch naming/organization
- Progress tracking for batch operations
- Individual file status tracking
- Batch metadata storage

#### Database Schema Updates

**New Table**: `batch_upload`
```sql
DEFINE TABLE batch_upload SCHEMAFULL;
DEFINE FIELD name ON TABLE batch_upload TYPE string;
DEFINE FIELD status ON TABLE batch_upload TYPE string DEFAULT "processing";
DEFINE FIELD total_files ON TABLE batch_upload TYPE int;
DEFINE FIELD processed_files ON TABLE batch_upload TYPE int DEFAULT 0;
DEFINE FIELD failed_files ON TABLE batch_upload TYPE int DEFAULT 0;
DEFINE FIELD created_at ON TABLE batch_upload TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON TABLE batch_upload TYPE datetime DEFAULT time::now();
```

**New Table**: `batch_source_relationship`
```sql
DEFINE TABLE batch_source_relationship SCHEMAFULL;
DEFINE FIELD batch_id ON TABLE batch_source_relationship TYPE record<batch_upload>;
DEFINE FIELD source_id ON TABLE batch_source_relationship TYPE record<source>;
DEFINE FIELD file_name ON TABLE batch_source_relationship TYPE string;
DEFINE FIELD status ON TABLE batch_source_relationship TYPE string DEFAULT "pending";
DEFINE FIELD error_message ON TABLE batch_source_relationship TYPE option<string>;
```

#### Background Processing Enhancements

**New Command**: `process_batch_sources`
```python
@command("process_batch_sources", app="open_notebook")
async def process_batch_sources_command(input_data: BatchProcessingInput):
    # Process each file individually
    # Update batch progress
    # Handle failures gracefully
    # Send notifications on completion
```

#### File Validation & Security

**Enhanced Validation**:
- Individual file size limits (configurable)
- Total batch size limits
- File type validation per file
- Virus scanning integration (optional)
- Duplicate detection within batch

### 1.2 Frontend Implementation

#### New Component: `BatchUploadDialog`

**Features**:
- Drag-and-drop zone for multiple files
- File list with individual status indicators
- Batch configuration options
- Progress bar for overall batch progress
- Individual file progress/status
- Pause/resume capabilities
- Error handling and retry options

**UI Structure**:
```tsx
interface BatchUploadDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: (batchId: string) => void
}

export function BatchUploadDialog({ open, onOpenChange, onSuccess }: BatchUploadDialogProps) {
  // Drag and drop handling
  // File validation
  // Upload progress tracking
  // Error management
}
```

#### Enhanced File Input Component

**New Component**: `MultiFileInput`
```tsx
interface MultiFileInputProps {
  onFilesSelected: (files: File[]) => void
  accept?: string
  maxFiles?: number
  maxSize?: number
  disabled?: boolean
}

export function MultiFileInput({ onFilesSelected, accept, maxFiles = 10, maxSize = 100 * 1024 * 1024 }: MultiFileInputProps) {
  // Multiple file selection
  // File preview
  // Validation feedback
}
```

#### Batch Management Interface

**New Page**: `/batch-uploads`
- List of all batch uploads
- Batch status and progress
- Individual file status within batches
- Batch actions (retry, cancel, delete)
- Batch search and filtering

#### Integration with Existing Upload Flow

**Enhanced Source Type Step**:
- Add "Batch Upload" option to existing source types
- Reuse existing validation and processing logic
- Maintain backward compatibility

### 1.3 Implementation Phases

**Phase 1: Backend Foundation** (2-3 days)
1. Create batch upload API endpoints
2. Implement database schema updates
3. Add batch processing commands
4. Create batch status tracking

**Phase 2: Core Frontend** (3-4 days)
1. Build batch upload dialog component
2. Implement drag-and-drop functionality
3. Add file validation and preview
4. Create progress tracking UI

**Phase 3: Advanced Features** (2-3 days)
1. Build batch management interface
2. Add pause/resume functionality
3. Implement retry mechanisms
4. Add batch notifications

**Phase 4: Integration & Polish** (1-2 days)
1. Integrate with existing source management
2. Add comprehensive error handling
3. Optimize performance
4. Add documentation and tests

---

## 2. Third-Party Service Connections

### 2.1 Service Integration Architecture

#### Plugin System Enhancement

**New Plugin Categories**:
- **Storage Services**: Google Drive, Dropbox, OneDrive, AWS S3
- **Cloud Processing**: Google Cloud Vision, AWS Textract, Azure Document AI
- **Collaboration**: Notion, Obsidian, Roam Research, GitHub
- **Communication**: Slack, Discord, Email services
- **Analytics**: Google Analytics, Custom analytics services

**Enhanced Plugin Interface**:
```python
class ExternalServicePlugin(BaseModel):
    name: str
    type: str  # storage, processing, collaboration, etc.
    version: str
    config_schema: Dict[str, Any]
    authentication: Dict[str, Any]
    capabilities: List[str]

    async def authenticate(self, credentials: Dict[str, Any]) -> bool
    async def test_connection(self) -> bool
    async def get_resources(self, filters: Dict[str, Any] = None) -> List[Dict]
    async def import_resource(self, resource_id: str, target_notebook: str) -> Source
    async def export_resource(self, source_id: str, target_service: str) -> bool
```

#### Service Configuration Management

**New Settings Structure**:
```python
class ExternalServiceSettings(RecordModel):
    enabled_services: List[str]
    service_configs: Dict[str, Dict[str, Any]]
    authentication_tokens: Dict[str, str]  # Encrypted storage
    sync_settings: Dict[str, Dict[str, Any]]
    webhook_endpoints: Dict[str, str]
```

#### Authentication System

**OAuth 2.0 Integration**:
```python
class OAuth2Manager:
    def get_authorization_url(self, service: str) -> str
    def exchange_code_for_token(self, service: str, code: str) -> str
    def refresh_token(self, service: str) -> str
    def validate_token(self, service: str) -> bool
```

**API Key Management**:
- Encrypted storage in database
- Rotation capabilities
- Usage tracking and limits

### 2.2 Storage Service Integrations

#### Google Drive Integration

**Plugin**: `GoogleDrivePlugin`
```python
class GoogleDrivePlugin(ExternalServicePlugin):
    async def list_files(self, folder_id: str = None, query: str = None) -> List[GoogleDriveFile]
    async def download_file(self, file_id: str) -> bytes
    async def get_file_metadata(self, file_id: str) -> GoogleDriveFile
    async def upload_file(self, file_content: bytes, filename: str, folder_id: str = None) -> GoogleDriveFile
```

**Features**:
- Browse Google Drive files
- Import documents as sources
- Export notes to Google Docs
- Real-time sync capabilities

#### Dropbox Integration

**Plugin**: `DropboxPlugin`
```python
class DropboxPlugin(ExternalServicePlugin):
    async def list_files(self, path: str = "") -> List[DropboxFile]
    async def download_file(self, file_path: str) -> bytes
    async def create_shared_link(self, file_path: str) -> str
    async def search_files(self, query: str) -> List[DropboxFile]
```

#### Cloud Storage Abstraction

**Interface**: `CloudStorageService`
```python
class CloudStorageService(ABC):
    @abstractmethod
    async def list_files(self, path: str = None, recursive: bool = False) -> List[CloudFile]

    @abstractmethod
    async def download_file(self, file_id: str) -> bytes

    @abstractmethod
    async def get_file_metadata(self, file_id: str) -> CloudFile

    @abstractmethod
    async def search_files(self, query: str, file_types: List[str] = None) -> List[CloudFile]
```

### 2.3 Collaboration Platform Integrations

#### Notion Integration

**Plugin**: `NotionPlugin`
```python
class NotionPlugin(ExternalServicePlugin):
    async def list_pages(self, database_id: str = None) -> List[NotionPage]
    async def get_page_content(self, page_id: str) -> str
    async def create_notebook_from_database(self, database_id: str) -> Notebook
    async def sync_notebook_to_notion(self, notebook_id: str, target_page_id: str) -> bool
```

**Features**:
- Import Notion pages as sources
- Create notebooks from Notion databases
- Two-way sync capabilities
- Rich content formatting preservation

#### GitHub Integration

**Plugin**: `GitHubPlugin`
```python
class GitHubPlugin(ExternalServicePlugin):
    async def list_repositories(self) -> List[GitHubRepo]
    async def get_repository_files(self, repo_name: str, path: str = "") -> List[GitHubFile]
    async def get_file_content(self, repo_name: str, file_path: str) -> str
    async def create_notebook_from_repo(self, repo_name: str) -> Notebook
```

### 2.4 API & Webhook System

#### Incoming Webhooks

**New Router**: `/api/webhooks`
```python
@router.post("/webhooks/{service}")
async def handle_webhook(service: str, payload: Dict[str, Any], signature: str = None):
    # Validate webhook signature
    # Process webhook payload
    # Trigger appropriate actions
    # Update sync status
```

**Supported Services**:
- GitHub repository events
- Google Drive file changes
- Slack messages and files
- Email attachments

#### Outgoing Webhooks

**Webhook Configuration**:
```python
class WebhookConfig(RecordModel):
    service: str
    event_types: List[str]
    url: str
    secret: str  # For signature validation
    active: bool = True
    retry_count: int = 3
```

### 2.5 Frontend Integration

#### Service Management UI

**New Page**: `/settings/integrations`
- Service connection management
- Authentication flows
- Configuration interfaces
- Sync status monitoring
- Usage statistics

**Components**:
- `ServiceConnectionCard`
- `OAuthFlowHandler`
- `SyncStatusIndicator`
- `ServiceConfigurationForm`

#### Import/Export Interface

**Enhanced Source Dialog**:
- Import from external services
- Batch import capabilities
- Sync progress tracking
- Conflict resolution

**New Component**: `ExternalSourcePicker`
```tsx
interface ExternalSourcePickerProps {
  onSourceSelected: (source: ExternalSource) => void
  enabledServices: string[]
  multiSelect: boolean
}

export function ExternalSourcePicker({ onSourceSelected, enabledServices, multiSelect }: ExternalSourcePickerProps) {
  // Service selection
  // Authentication flows
  // File/folder browsing
  // Source preview
}
```

### 2.6 Implementation Phases

**Phase 1: Plugin Architecture** (3-4 days)
1. Enhance plugin system architecture
2. Create service abstractions
3. Implement authentication framework
4. Build configuration management

**Phase 2: Storage Services** (4-5 days)
1. Implement Google Drive integration
2. Add Dropbox integration
3. Create cloud storage abstraction
4. Build import/export UI

**Phase 3: Collaboration Platforms** (4-5 days)
1. Implement Notion integration
2. Add GitHub integration
3. Create collaboration UI
4. Implement sync capabilities

**Phase 4: Webhooks & Automation** (3-4 days)
1. Build webhook system
2. Implement automation rules
3. Add notification system
4. Create monitoring dashboard

---

## 3. Enhanced Mobile Support

### 3.1 Responsive Design Overhaul

#### Mobile-First Layout System

**Responsive Sidebar Navigation**:
```tsx
// New responsive sidebar component
export function ResponsiveSidebar() {
  const [isMobile, setIsMobile] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Mobile: off-canvas drawer
  // Tablet: collapsible sidebar
  // Desktop: fixed sidebar

  return (
    <>
      {/* Mobile menu button */}
      <Button
        variant="ghost"
        size="sm"
        className="md:hidden fixed top-4 left-4 z-50"
        onClick={() => setSidebarOpen(true)}
      >
        <Menu className="h-5 w-5" />
      </Button>

      {/* Sidebar */}
      <div className={cn(
        "fixed inset-y-0 left-0 z-40 w-64 bg-sidebar border-r transform transition-transform duration-300 ease-in-out",
        sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
        isMobile && !sidebarOpen && "hidden"
      )}>
        {/* Sidebar content */}
      </div>

      {/* Mobile overlay */}
      {isMobile && sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </>
  )
}
```

**Adaptive Grid System**:
```tsx
// Responsive grid layouts for different screen sizes
export function ResponsiveGrid({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {children}
    </div>
  )
}
```

#### Touch-Optimized Components

**Mobile Navigation**:
```tsx
// Bottom navigation for mobile
export function MobileNavigation() {
  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-background border-t">
      <div className="grid grid-cols-4 h-16">
        <MobileNavItem icon={Home} label="Home" href="/" />
        <MobileNavItem icon={BookOpen} label="Notebooks" href="/notebooks" />
        <MobileNavItem icon={FileText} label="Sources" href="/sources" />
        <MobileNavItem icon={Settings} label="Settings" href="/settings" />
      </div>
    </nav>
  )
}
```

**Touch-Friendly Buttons**:
```tsx
// Enhanced button component with touch feedback
export function TouchButton({ children, ...props }: ButtonProps) {
  return (
    <Button
      {...props}
      className={cn(
        "min-h-[44px] min-w-[44px] touch-manipulation", // WCAG touch targets
        "active:scale-95 transition-transform", // Touch feedback
        props.className
      )}
    >
      {children}
    </Button>
  )
}
```

### 3.2 Mobile-Specific Features

#### Gesture Support

**Swipe Gestures**:
```tsx
// Swipe to navigate between pages
export function useSwipeNavigation() {
  useEffect(() => {
    let touchStartX = 0
    let touchEndX = 0

    const handleTouchStart = (e: TouchEvent) => {
      touchStartX = e.changedTouches[0].screenX
    }

    const handleTouchEnd = (e: TouchEvent) => {
      touchEndX = e.changedTouches[0].screenX
      handleSwipe()
    }

    const handleSwipe = () => {
      const swipeThreshold = 50
      const diff = touchStartX - touchEndX

      if (Math.abs(diff) > swipeThreshold) {
        if (diff > 0) {
          // Swipe left - go to next page
          navigateNext()
        } else {
          // Swipe right - go to previous page
          navigatePrevious()
        }
      }
    }

    document.addEventListener('touchstart', handleTouchStart)
    document.addEventListener('touchend', handleTouchEnd)

    return () => {
      document.removeEventListener('touchstart', handleTouchStart)
      document.removeEventListener('touchend', handleTouchEnd)
    }
  }, [])
}
```

**Pull-to-Refresh**:
```tsx
export function PullToRefresh({ onRefresh, children }: PullToRefreshProps) {
  const [pulling, setPulling] = useState(false)
  const [pullDistance, setPullDistance] = useState(0)

  // Implement pull-to-refresh gesture
  // Show loading indicator
  // Trigger refresh callback
}
```

#### Mobile Upload Experience

**Camera Integration**:
```tsx
export function MobileCameraInput({ onCapture }: MobileCameraInputProps) {
  const handleCameraCapture = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }
      })
      // Camera interface
      // Image capture
      // File processing
    } catch (error) {
      console.error('Camera access denied:', error)
    }
  }

  return (
    <Button onClick={handleCameraCapture} className="w-full">
      <Camera className="h-4 w-4 mr-2" />
      Take Photo
    </Button>
  )
}
```

**Voice Input**:
```tsx
export function VoiceInput({ onTranscript }: VoiceInputProps) {
  const [recording, setRecording] = useState(false)

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      // Speech recognition setup
      // Real-time transcription
    } catch (error) {
      console.error('Microphone access denied:', error)
    }
  }

  return (
    <Button
      variant={recording ? "destructive" : "outline"}
      onClick={recording ? stopRecording : startRecording}
    >
      <Mic className={cn("h-4 w-4", recording && "animate-pulse")} />
      {recording ? "Stop Recording" : "Voice Input"}
    </Button>
  )
}
```

### 3.3 Performance Optimization

#### Mobile-Specific Optimizations

**Lazy Loading**:
```tsx
// Intersection Observer for lazy loading
export function useLazyLoad() {
  const [ref, inView] = useInView({
    threshold: 0.1,
    triggerOnce: true
  })

  return { ref, shouldLoad: inView }
}
```

**Progressive Web App Features**:
```tsx
// Service worker registration
export function registerServiceWorker() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js')
      .then(registration => {
        console.log('SW registered:', registration)
      })
      .catch(error => {
        console.log('SW registration failed:', error)
      })
  }
}
```

**Offline Support**:
```tsx
// IndexedDB for offline storage
export function useOfflineStorage() {
  const store = useIndexedDB('open-notebook-offline')

  const saveOffline = async (key: string, data: any) => {
    await store.put(key, data)
  }

  const getOffline = async (key: string) => {
    return await store.get(key)
  }

  return { saveOffline, getOffline }
}
```

### 3.4 Mobile Configuration

#### Viewport and Meta Tags

**Enhanced HTML Head**:
```html
<!-- In layout.tsx -->
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="default" />
  <meta name="format-detection" content="telephone=no" />
  <meta name="msapplication-TileColor" content="#000000" />
  <meta name="theme-color" content="#ffffff" />
</head>
```

#### Mobile-Specific CSS

**Touch Feedback Styles**:
```css
/* globals.css */
.touch-feedback {
  -webkit-tap-highlight-color: rgba(0, 0, 0, 0.1);
  touch-action: manipulation;
}

/* Smooth scrolling */
.smooth-scroll {
  -webkit-overflow-scrolling: touch;
  scroll-behavior: smooth;
}

/* Prevent zoom on input focus */
input, textarea, select {
  font-size: 16px; /* Prevents zoom on iOS */
}
```

### 3.5 Mobile Testing Strategy

#### Device Testing
- iPhone (iOS 14+)
- Android (various versions)
- iPad (tablet experience)
- Various screen sizes

#### Performance Testing
- Lighthouse mobile audit
- Core Web Vitals monitoring
- Network throttling scenarios
- Offline functionality testing

### 3.6 Implementation Phases

**Phase 1: Responsive Foundation** (2-3 days)
1. Implement mobile-first layouts
2. Create responsive sidebar navigation
3. Add mobile navigation components
4. Optimize touch targets

**Phase 2: Mobile Features** (3-4 days)
1. Implement gesture support
2. Add mobile camera integration
3. Create voice input functionality
4. Build pull-to-refresh feature

**Phase 3: Performance Optimization** (2-3 days)
1. Implement lazy loading
2. Add PWA features
3. Create offline support
4. Optimize bundle size

**Phase 4: Polish & Testing** (1-2 days)
1. Comprehensive mobile testing
2. Performance optimization
3. Accessibility improvements
4. Documentation updates

---

## 4. Advanced Message Rendering

### 4.1 Current Message System Analysis

#### Existing Chat Infrastructure
- **Chat Component**: Located in `frontend/src/components/chat/`
- **Message Types**: Text-only messages with basic formatting
- **Rendering**: Simple text display with markdown support
- **Interactions**: Basic copy, edit, delete functionality
- **Citations**: Basic reference system with numbered citations

#### Limitations of Current System
- **Text-Only**: No multimedia support (images, videos, audio)
- **Static Content**: No interactive elements or embedded widgets
- **Limited Formatting**: Basic markdown without advanced formatting
- **No Collaboration**: No real-time collaboration features
- **Poor Mobile Experience**: Message rendering not optimized for mobile screens

### 4.2 Enhanced Message Architecture

#### Message Data Model Enhancement

**Extended Message Schema**:
```typescript
interface EnhancedMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: MessageContent[]
  timestamp: Date
  metadata: MessageMetadata
  reactions: MessageReaction[]
  attachments: MessageAttachment[]
  citations: MessageCitation[]
  status: MessageStatus
  edited?: boolean
  editedAt?: Date
}

interface MessageContent {
  type: 'text' | 'image' | 'video' | 'audio' | 'code' | 'table' | 'chart' | 'widget' | 'file'
  content: any
  metadata?: ContentMetadata
}

interface MessageAttachment {
  id: string
  type: 'image' | 'document' | 'audio' | 'video' | 'dataset'
  url: string
  name: string
  size: number
  mimeType: string
  thumbnail?: string
}
```

#### Message Rendering Pipeline

**Content Processing Pipeline**:
```typescript
class MessageRenderer {
  async renderMessage(message: EnhancedMessage): Promise<JSX.Element> {
    const renderedContent = await Promise.all(
      message.content.map(content => this.renderContent(content))
    )

    return (
      <MessageContainer message={message}>
        {renderedContent}
        <MessageActions message={message} />
        <MessageReactions reactions={message.reactions} />
        <MessageCitations citations={message.citations} />
      </MessageContainer>
    )
  }

  private async renderContent(content: MessageContent): Promise<JSX.Element> {
    switch (content.type) {
      case 'text':
        return <TextRenderer content={content.content} />
      case 'image':
        return <ImageRenderer content={content.content} />
      case 'code':
        return <CodeRenderer content={content.content} />
      case 'chart':
        return <ChartRenderer content={content.content} />
      // ... other content types
    }
  }
}
```

### 4.3 Rich Content Support

#### Enhanced Text Rendering

**Markdown++ Renderer**:
```tsx
export function EnhancedTextRenderer({ content }: { content: string }) {
  const processedContent = useMemo(() => {
    return processAdvancedMarkdown(content)
  }, [content])

  return (
    <div className="prose prose-sm max-w-none dark:prose-invert">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath, remarkMermaid]}
        rehypePlugins={[rehypeHighlight, rehypeKatex]}
        components={{
          // Custom component mappings
          code: CodeBlock,
          math: MathBlock,
          mermaid: MermaidDiagram,
          table: EnhancedTable,
          img: SmartImage,
          a: SmartLink,
        }}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  )
}
```

**Advanced Features**:
- **Mermaid Diagrams**: Flowcharts, sequence diagrams, Gantt charts
- **Mathematical Equations**: LaTeX rendering with KaTeX
- **Syntax Highlighting**: Enhanced code blocks with language detection
- **Interactive Tables**: Sortable, filterable data tables
- **Smart Links**: Link previews, embedded content
- **Footnotes & Citations**: Academic-style referencing

#### Multimedia Content Rendering

**Image Rendering with Analysis**:
```tsx
export function ImageRenderer({ attachment, enableAnalysis = true }: ImageRendererProps) {
  const [analysis, setAnalysis] = useState<ImageAnalysis | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  const analyzeImage = async () => {
    setIsAnalyzing(true)
    try {
      const result = await analyzeImageContent(attachment.url)
      setAnalysis(result)
    } catch (error) {
      console.error('Image analysis failed:', error)
    } finally {
      setIsAnalyzing(false)
    }
  }

  return (
    <div className="relative group">
      <img
        src={attachment.url}
        alt={attachment.name}
        className="max-w-full h-auto rounded-lg shadow-sm"
        loading="lazy"
      />

      {/* Image analysis overlay */}
      {enableAnalysis && (
        <Button
          variant="outline"
          size="sm"
          className="absolute top-2 right-2 opacity-0 group-hover:opacity-100"
          onClick={analyzeImage}
          disabled={isAnalyzing}
        >
          {isAnalyzing ? <Loader className="h-3 w-3 animate-spin" /> : <Eye className="h-3 w-3" />}
          Analyze
        </Button>
      )}

      {/* Analysis results */}
      {analysis && (
        <div className="mt-2 p-3 bg-muted rounded-lg">
          <h4 className="font-medium text-sm mb-1">Image Analysis</h4>
          <p className="text-xs text-muted-foreground">{analysis.description}</p>
          {analysis.objects && (
            <div className="mt-2 flex flex-wrap gap-1">
              {analysis.objects.map(obj => (
                <Badge key={obj} variant="secondary" className="text-xs">
                  {obj}
                </Badge>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
```

**Audio Message Support**:
```tsx
export function AudioRenderer({ attachment }: { attachment: MessageAttachment }) {
  const [transcript, setTranscript] = useState<string | null>(null)
  const [isTranscribing, setIsTranscribing] = useState(false)

  return (
    <div className="space-y-3">
      {/* Audio player */}
      <audio
        controls
        className="w-full"
        src={attachment.url}
      >
        Your browser does not support the audio element.
      </audio>

      {/* Transcription */}
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={transcribeAudio}
          disabled={isTranscribing}
        >
          {isTranscribing ? <Loader className="h-3 w-3 animate-spin mr-1" /> : <FileText className="h-3 w-3 mr-1" />}
          Transcribe
        </Button>
      </div>

      {transcript && (
        <div className="p-3 bg-muted rounded-lg">
          <h4 className="font-medium text-sm mb-2">Transcript</h4>
          <p className="text-sm">{transcript}</p>
        </div>
      )}
    </div>
  )
}
```

#### Interactive Content Widgets

**Data Visualization**:
```tsx
export function ChartRenderer({ chartData }: { chartData: ChartData }) {
  return (
    <div className="w-full h-80 my-4">
      <ResponsiveContainer width="100%" height="100%">
        {chartData.type === 'line' && (
          <LineChart data={chartData.data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={chartData.xAxis} />
            <YAxis />
            <Tooltip />
            <Legend />
            {chartData.series.map((series, index) => (
              <Line
                key={series.name}
                type="monotone"
                dataKey={series.key}
                stroke={COLORS[index % COLORS.length]}
                strokeWidth={2}
              />
            ))}
          </LineChart>
        )}
        {/* Other chart types: bar, pie, area, scatter */}
      </ResponsiveContainer>
    </div>
  )
}
```

**Interactive Code Execution**:
```tsx
export function ExecutableCodeBlock({ code, language }: { code: string, language: string }) {
  const [output, setOutput] = useState<string | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const executeCode = async () => {
    setIsRunning(true)
    setError(null)

    try {
      const result = await executeCodeSandbox(code, language)
      setOutput(result.output)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Execution failed')
    } finally {
      setIsRunning(false)
    }
  }

  return (
    <div className="relative">
      <CodeBlock code={code} language={language} />

      {/* Execute button for supported languages */}
      {['python', 'javascript', 'typescript', 'sql'].includes(language) && (
        <div className="absolute top-2 right-2">
          <Button
            variant="outline"
            size="sm"
            onClick={executeCode}
            disabled={isRunning}
          >
            {isRunning ? (
              <Loader className="h-3 w-3 animate-spin mr-1" />
            ) : (
              <Play className="h-3 w-3 mr-1" />
            )}
            Run
          </Button>
        </div>
      )}

      {/* Output display */}
      {output && (
        <div className="mt-2 p-3 bg-black text-green-400 rounded-lg font-mono text-sm">
          <div className="text-xs text-gray-400 mb-1">Output:</div>
          {output}
        </div>
      )}

      {error && (
        <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded-lg">
          <div className="text-xs text-red-600 mb-1">Error:</div>
          <div className="text-sm text-red-800">{error}</div>
        </div>
      )}
    </div>
  )
}
```

### 4.4 Real-Time Collaboration Features

#### Live Typing Indicators

**Typing Indicator Component**:
```tsx
export function TypingIndicator({ users }: { users: TypingUser[] }) {
  if (users.length === 0) return null

  const getTypingText = () => {
    if (users.length === 1) {
      return `${users[0].name} is typing...`
    } else if (users.length === 2) {
      return `${users[0].name} and ${users[1].name} are typing...`
    } else {
      return `${users[0].name} and ${users.length - 1} others are typing...`
    }
  }

  return (
    <div className="flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground">
      <div className="flex gap-1">
        {users.map((user, index) => (
          <div
            key={user.id}
            className="w-2 h-2 bg-primary rounded-full animate-bounce"
            style={{ animationDelay: `${index * 0.1}s` }}
          />
        ))}
      </div>
      <span>{getTypingText()}</span>
    </div>
  )
}
```

#### Message Reactions & Responses

**Reaction System**:
```tsx
export function MessageReactions({ messageId, reactions, onReactionAdd }: MessageReactionsProps) {
  const [showEmojiPicker, setShowEmojiPicker] = useState(false)

  const groupedReactions = reactions.reduce((acc, reaction) => {
    if (!acc[reaction.emoji]) {
      acc[reaction.emoji] = { count: 0, users: [] }
    }
    acc[reaction.emoji].count++
    acc[reaction.emoji].users.push(reaction.user)
    return acc
  }, {} as Record<string, { count: number; users: string[] }>)

  return (
    <div className="flex items-center gap-2 mt-2">
      {Object.entries(groupedReactions).map(([emoji, data]) => (
        <Button
          key={emoji}
          variant="outline"
          size="sm"
          className="h-6 px-2 text-xs hover:bg-muted"
          onClick={() => onReactionAdd(messageId, emoji)}
        >
          {emoji} {data.count}
        </Button>
      ))}

      <Button
        variant="ghost"
        size="sm"
        className="h-6 w-6 p-0"
        onClick={() => setShowEmojiPicker(!showEmojiPicker)}
      >
        <Smile className="h-3 w-3" />
      </Button>

      {showEmojiPicker && (
        <EmojiPicker
          onEmojiSelect={(emoji) => {
            onReactionAdd(messageId, emoji)
            setShowEmojiPicker(false)
          }}
        />
      )}
    </div>
  )
}
```

#### Message Threads & Replies

**Thread System**:
```tsx
export function MessageThread({ parentMessage, replies, onReply }: MessageThreadProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [replyContent, setReplyContent] = useState('')

  return (
    <div className="border-l-2 border-muted pl-4 ml-4">
      {/* Parent message reference */}
      <div className="text-xs text-muted-foreground mb-2">
        Replying to {parentMessage.role === 'user' ? 'your' : "assistant's"} message
      </div>

      {/* Thread content */}
      {isExpanded && (
        <div className="space-y-3">
          {replies.map(reply => (
            <MessageComponent key={reply.id} message={reply} isThreaded />
          ))}
        </div>
      )}

      {/* Reply input */}
      <div className="mt-3 flex gap-2">
        <Input
          value={replyContent}
          onChange={(e) => setReplyContent(e.target.value)}
          placeholder="Write a reply..."
          className="flex-1"
        />
        <Button
          size="sm"
          onClick={() => {
            if (replyContent.trim()) {
              onReply(parentMessage.id, replyContent)
              setReplyContent('')
            }
          }}
        >
          Send
        </Button>
      </div>

      {/* Expand/collapse toggle */}
      {replies.length > 0 && (
        <Button
          variant="ghost"
          size="sm"
          className="mt-2 text-xs"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          {isExpanded ? 'Hide' : 'Show'} {replies.length} {replies.length === 1 ? 'reply' : 'replies'}
        </Button>
      )}
    </div>
  )
}
```

### 4.5 Enhanced Mobile Message Experience

#### Mobile-Optimized Message Layout

**Responsive Message Components**:
```tsx
export function MobileMessage({ message }: { message: EnhancedMessage }) {
  return (
    <div className="touch-manipulation">
      {/* Swipe actions */}
      <SwipeActions
        leftActions={[
          { icon: Reply, label: 'Reply', action: () => onReply(message.id) },
          { icon: Share, label: 'Share', action: () => onShare(message.id) }
        ]}
        rightActions={[
          { icon: Copy, label: 'Copy', action: () => onCopy(message.id) },
          { icon: MoreVertical, label: 'More', action: () => onMore(message.id) }
        ]}
      >
        <div className="px-4 py-3">
          {/* Message content optimized for mobile */}
          <div className="prose prose-sm max-w-none">
            <MobileContentRenderer content={message.content} />
          </div>

          {/* Mobile-optimized actions */}
          <div className="flex gap-2 mt-3">
            <TouchButton size="sm" variant="outline">
              <ThumbsUp className="h-3 w-3" />
            </TouchButton>
            <TouchButton size="sm" variant="outline">
              <MessageSquare className="h-3 w-3" />
            </TouchButton>
            <TouchButton size="sm" variant="outline">
              <Share className="h-3 w-3" />
            </TouchButton>
          </div>
        </div>
      </SwipeActions>
    </div>
  )
}
```

#### Voice Message Support

**Mobile Voice Recording**:
```tsx
export function VoiceMessageRecorder({ onSend }: VoiceMessageRecorderProps) {
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      const chunks: Blob[] = []

      mediaRecorder.ondataavailable = (e) => chunks.push(e.data)
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'audio/webm' })
        setAudioBlob(blob)
      }

      mediaRecorder.start()
      setIsRecording(true)

      // Start timer
      const timer = setInterval(() => {
        setRecordingTime(prev => prev + 1)
      }, 1000)

      // Stop recording after max 60 seconds
      setTimeout(() => {
        if (mediaRecorder.state === 'recording') {
          mediaRecorder.stop()
          clearInterval(timer)
          setIsRecording(false)
        }
      }, 60000)
    } catch (error) {
      console.error('Recording failed:', error)
    }
  }

  const stopRecording = () => {
    // Stop media recorder logic
    setIsRecording(false)
  }

  const sendVoiceMessage = () => {
    if (audioBlob) {
      onSend(audioBlob)
      setAudioBlob(null)
      setRecordingTime(0)
    }
  }

  return (
    <div className="flex items-center gap-3 p-4 bg-muted rounded-lg">
      {isRecording ? (
        <>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
            <span className="text-sm font-mono">
              {Math.floor(recordingTime / 60)}:{(recordingTime % 60).toString().padStart(2, '0')}
            </span>
          </div>
          <TouchButton onClick={stopRecording} variant="destructive">
            <Square className="h-4 w-4" />
          </TouchButton>
        </>
      ) : audioBlob ? (
        <>
          <audio src={URL.createObjectURL(audioBlob)} controls className="flex-1" />
          <TouchButton onClick={sendVoiceMessage}>
            <Send className="h-4 w-4" />
          </TouchButton>
          <TouchButton onClick={() => setAudioBlob(null)} variant="outline">
            <Trash2 className="h-4 w-4" />
          </TouchButton>
        </>
      ) : (
        <TouchButton onClick={startRecording} className="w-full">
          <Mic className="h-4 w-4 mr-2" />
          Hold to Record
        </TouchButton>
      )}
    </div>
  )
}
```

### 4.6 Backend Enhancements for Rich Messages

#### Enhanced Message Storage

**Database Schema Updates**:
```sql
-- Enhanced message table
DEFINE TABLE message SCHEMAFULL;
DEFINE FIELD content ON TABLE message TYPE array; -- Array of content blocks
DEFINE FIELD attachments ON TABLE message TYPE array; -- Array of attachment objects
DEFINE FIELD metadata ON TABLE message TYPE object; -- Message metadata
DEFINE FIELD reactions ON TABLE message TYPE array; -- Message reactions
DEFINE FIELD thread_id ON TABLE message TYPE option<record<message>>; -- Thread parent
DEFINE FIELD reply_count ON TABLE message TYPE int DEFAULT 0; -- Reply count
DEFINE FIELD edited ON TABLE message TYPE bool DEFAULT false;
DEFINE FIELD edited_at ON TABLE message TYPE option<datetime>;

-- Attachments table
DEFINE TABLE attachment SCHEMAFULL;
DEFINE FIELD message_id ON TABLE attachment TYPE record<message>;
DEFINE FIELD type ON TABLE attachment TYPE string; -- image, audio, video, document
DEFINE FIELD url ON TABLE attachment TYPE string;
DEFINE FIELD name ON TABLE attachment TYPE string;
DEFINE FIELD size ON TABLE attachment TYPE int;
DEFINE FIELD mime_type ON TABLE attachment TYPE string;
DEFINE FIELD metadata ON TABLE attachment TYPE object; -- Attachment-specific metadata

-- Reactions table
DEFINE TABLE reaction SCHEMAFULL;
DEFINE FIELD message_id ON TABLE reaction TYPE record<message>;
DEFINE FIELD user_id ON TABLE reaction TYPE string;
DEFINE FIELD emoji ON TABLE reaction TYPE string;
DEFINE FIELD created_at ON TABLE reaction TYPE datetime DEFAULT time::now();
```

#### File Processing Pipeline

**Enhanced File Processor**:
```python
class RichContentProcessor:
    def __init__(self):
        self.image_processor = ImageProcessor()
        self.audio_processor = AudioProcessor()
        self.video_processor = VideoProcessor()
        self.document_processor = DocumentProcessor()

    async def process_attachment(self, file_data: bytes, mime_type: str) -> ProcessedAttachment:
        """Process uploaded file and extract metadata"""
        if mime_type.startswith('image/'):
            return await self.image_processor.process(file_data)
        elif mime_type.startswith('audio/'):
            return await self.audio_processor.process(file_data)
        elif mime_type.startswith('video/'):
            return await self.video_processor.process(file_data)
        else:
            return await self.document_processor.process(file_data)

    async def generate_thumbnails(self, attachment: ProcessedAttachment) -> List[str]:
        """Generate thumbnails for different preview sizes"""
        thumbnails = []

        if attachment.type == 'image':
            # Generate multiple thumbnail sizes
            for size in [150, 300, 600]:
                thumbnail_url = await self.image_processor.generate_thumbnail(
                    attachment.url, size
                )
                thumbnails.append(thumbnail_url)

        return thumbnails

    async def analyze_content(self, attachment: ProcessedAttachment) -> ContentAnalysis:
        """Analyze attachment content for searchability and insights"""
        if attachment.type == 'image':
            return await self.image_processor.analyze(attachment.url)
        elif attachment.type == 'audio':
            return await self.audio_processor.transcribe(attachment.url)
        elif attachment.type == 'document':
            return await self.document_processor.extract_text(attachment.url)
```

#### AI Integration for Content Enhancement

**Content Analysis Service**:
```python
class ContentAnalysisService:
    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager

    async def analyze_image(self, image_url: str) -> ImageAnalysis:
        """Analyze image content using vision models"""
        vision_model = await self.model_manager.get_model("gpt-4-vision-preview")

        prompt = """
        Analyze this image and provide:
        1. A detailed description
        2. Key objects or elements detected
        3. Text content (if any)
        4. Potential tags for categorization
        """

        response = await vision_model.ainvoke([
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_url}}
        ])

        return ImageAnalysis.from_response(response.content)

    async def extract_insights(self, content: str, context: str = "") -> List[ContentInsight]:
        """Extract key insights from content"""
        analysis_model = await self.model_manager.get_model("gpt-4")

        prompt = f"""
        Analyze the following content and extract key insights:

        Content: {content}
        Context: {context}

        Provide insights in JSON format with:
        - key_points: Main points extracted
        - questions: Questions raised by the content
        - connections: Potential connections to other topics
        - action_items: Any actionable items
        """

        response = await analysis_model.ainvoke(prompt)
        return ContentInsight.from_json(response.content)
```

### 4.7 Message Search & Discovery

#### Advanced Search Capabilities

**Enhanced Search Index**:
```typescript
interface SearchIndex {
  messages: Map<string, SearchableMessage>
  contentBlocks: Map<string, SearchableContent>
  attachments: Map<string, SearchableAttachment>
  semanticIndex: SemanticSearchIndex
}

interface SearchableMessage {
  id: string
  text: string
  embeddings: number[]
  metadata: {
    timestamp: Date
    author: string
    notebook: string
    tags: string[]
    contentType: string[]
  }
}

export class MessageSearchService {
  async searchMessages(query: string, filters: SearchFilters): Promise<SearchResult[]> {
    // Multi-modal search: text + semantic + metadata
    const textResults = await this.textSearch(query)
    const semanticResults = await this.semanticSearch(query)
    const filteredResults = this.applyFilters([...textResults, ...semanticResults], filters)

    return this.rankAndDeduplicate(filteredResults)
  }

  async searchByContent(contentType: string, query: string): Promise<SearchResult[]> {
    switch (contentType) {
      case 'images':
        return this.searchImages(query)
      case 'audio':
        return this.searchAudioTranscripts(query)
      case 'documents':
        return this.searchDocuments(query)
      default:
        return this.searchText(query)
    }
  }

  async searchSimilarMessages(messageId: string): Promise<SearchResult[]> {
    const message = await this.getMessage(messageId)
    return this.semanticSearch(message.content)
  }
}
```

### 4.8 Implementation Phases

**Phase 1: Enhanced Text Rendering** (3-4 days)
1. Implement advanced markdown renderer
2. Add mathematical equation support
3. Create enhanced code blocks with syntax highlighting
4. Build interactive table components

**Phase 2: Multimedia Support** (4-5 days)
1. Implement image rendering with analysis
2. Add audio message support with transcription
3. Create video embedding and playback
4. Build file attachment system

**Phase 3: Interactive Content** (3-4 days)
1. Implement chart and data visualization
2. Add executable code blocks
3. Create interactive widgets and forms
4. Build real-time collaboration features

**Phase 4: Mobile Optimization** (2-3 days)
1. Optimize message rendering for mobile
2. Implement voice message recording
3. Add touch interactions and gestures
4. Create mobile-specific UI components

**Phase 5: Search & Discovery** (2-3 days)
1. Build advanced search functionality
2. Implement semantic search
3. Create content-based recommendations
4. Add intelligent content organization

---

## 5. Implementation Timeline

### Total Estimated Duration: 4-5 weeks

**Week 1: Foundation**
- Batch upload backend implementation
- Plugin architecture enhancement
- Responsive design foundation
- Enhanced text rendering pipeline

**Week 2: Core Features**
- Batch upload frontend
- Storage service integrations
- Mobile navigation implementation
- Multimedia message support

**Week 3: Advanced Features**
- Batch management interface
- Collaboration platform integrations
- Mobile-specific features
- Interactive content widgets

**Week 4: Rich Content & Search**
- Real-time collaboration features
- Message search & discovery
- Mobile voice messaging
- Third-party webhooks & automation

**Week 5: Polish & Integration**
- Testing and optimization
- Documentation
- Performance tuning
- Final integration testing

---

## 6. Technical Considerations

### 6.1 Security

- **File Upload Security**: Enhanced validation, virus scanning, sandboxing
- **Third-Party Authentication**: OAuth 2.0 best practices, token encryption
- **API Security**: Rate limiting, input validation, CORS configuration
- **Content Security**: XSS prevention, content sanitization, CSP policies
- **Data Privacy**: GDPR compliance, data encryption, user consent

### 6.2 Scalability

- **Batch Processing**: Queue management, resource allocation, progress tracking
- **Third-Party APIs**: Rate limiting, caching strategies, error handling
- **Message Storage**: Efficient indexing, compression, archival strategies
- **Mobile Performance**: Bundle optimization, image compression, caching
- **Real-time Features**: WebSocket management, connection pooling

### 6.3 Maintainability

- **Modular Architecture**: Clear separation of concerns, plugin system
- **Testing Strategy**: Unit tests, integration tests, E2E tests
- **Documentation**: API documentation, user guides, developer docs
- **Code Quality**: TypeScript strict mode, linting, code reviews
- **Component Reusability**: Design system, component library

### 6.4 User Experience

- **Progressive Enhancement**: Core functionality works everywhere
- **Accessibility**: WCAG 2.1 AA compliance, screen reader support
- **Error Handling**: Graceful degradation, clear error messages
- **Onboarding**: Guided tours, tooltips, help documentation
- **Performance**: Fast rendering, smooth animations, responsive interactions

---

## 7. Success Metrics

### 7.1 Batch Upload Feature
- **Adoption Rate**: % of users using batch upload within 30 days
- **Efficiency**: Average time saved compared to individual uploads
- **Success Rate**: % of batch uploads completed successfully
- **User Satisfaction**: Feedback scores and feature requests

### 7.2 Third-Party Integrations
- **Connection Rate**: % of users connecting external services
- **Usage Frequency**: Average sync operations per user per week
- **Integration Success**: % of successful imports/exports
- **Service Coverage**: Number of supported services

### 7.3 Mobile Support
- **Mobile Usage**: % of traffic from mobile devices
- **Performance**: Core Web Vitals scores on mobile
- **User Engagement**: Session duration on mobile vs desktop
- **Conversion**: Task completion rates on mobile

### 7.4 Advanced Message Rendering
- **Rich Content Usage**: % of messages containing multimedia or interactive elements
- **User Engagement**: Interaction rates with reactions, threads, and collaborative features
- **Search Effectiveness**: Success rates for advanced content search
- **Mobile Message Experience**: Message interaction rates on mobile devices
- **Content Quality**: User satisfaction with enhanced formatting and features

---

## 8. Next Steps

1. **Stakeholder Review**: Present plan to team for feedback and approval
2. **Prioritization**: Determine feature order based on user needs and technical constraints
3. **Resource Allocation**: Assign developers to specific feature areas
4. **Development Environment**: Set up testing environments and CI/CD pipelines
5. **User Research**: Conduct user interviews to validate feature assumptions
6. **Technical Spikes**: Implement proof-of-concepts for high-risk areas
7. **Documentation**: Update technical documentation and API specs

---

This comprehensive plan provides a roadmap for significantly enhancing Open Notebook's functionality while maintaining the project's core values of privacy, flexibility, and user control. The modular approach ensures that features can be developed incrementally and tested thoroughly before release.