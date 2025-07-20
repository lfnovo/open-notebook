# Open Notebook Frontend Migration Guide

## Overview

This document outlines the current Streamlit-based interface of Open Notebook to guide the migration to a React/Shadcn-based UI. The analysis covers all existing pages, their layouts, components, and features.

## Current Technology Stack

- **Frontend Framework**: Streamlit with multi-page architecture
- **UI Components**: Native Streamlit components + custom fragments
- **State Management**: `st.session_state` with fragment-based updates
- **Authentication**: Custom auth system with password protection
- **Code Editor**: Monaco editor integration for markdown
- **Audio**: HTML5 audio player for podcast playback

## Page Structure and Navigation

### Main Entry Point
- **File**: `app_home.py`
- **Function**: Object routing and redirection
- **Features**: Dynamic routing based on `object_id` query parameters

### Navigation System
Streamlit sidebar-based navigation with numbered page files:

1. **Home** (app_home.py) - Object routing
2. **📒 Notebooks** (pages/2_📒_Notebooks.py)
3. **🔍 Ask and Search** (pages/3_🔍_Ask_and_Search.py)
4. **🎙️ Podcasts** (pages/5_🎙️_Podcasts.py)
5. **🤖 Models** (pages/7_🤖_Models.py)
6. **💱 Transformations** (pages/8_💱_Transformations.py)
7. **⚙️ Settings** (pages/10_⚙️_Settings.py)

---

## Page-by-Page Analysis

### 1. 📒 Notebooks Page

**Primary Function**: Main workspace for research project management

#### Layout Structure
- **Dual State Interface**:
  - **List View**: Grid of notebook cards with creation interface
  - **Individual Notebook View**: Three-column layout (sources, notes, chat)

#### Key Features
- **Notebook Management**:
  - Create new notebooks with expandable form
  - Edit notebook name and description inline
  - Archive/unarchive functionality
  - Permanent deletion with confirmation
  
- **Three-Column Layout**:
  - **Left Column**: Sources management
  - **Middle Column**: Notes display and creation
  - **Right Column**: Chat interface with sessions

#### Components
- Expandable notebook creation form
- Dynamic notebook header with edit capabilities
- Source cards with context indicators
- Note cards (human vs AI generated)
- Chat sidebar with session management
- Context control panel

#### UI Patterns
- Expandable sections for forms
- Card-based display for content
- Modal dialogs for detailed editing
- Tab-based organization within sections

---

### 2. 🔍 Ask and Search Page

**Primary Function**: Cross-notebook search and AI querying

#### Layout Structure
- **Tab-Based Interface**:
  - **"Ask Your Knowledge Base"** tab
  - **"Search"** tab

#### Key Features
- **AI Querying**:
  - Multi-model selection (Language, Embedding, TTS, STT)
  - Question input with notebook selection
  - Response saving as notes
  
- **Search Functionality**:
  - Search type selection (text vs vector)
  - Content type filtering
  - Score-based results ranking
  - Expandable match details

#### Components
- Model selector component (reusable)
- Search filter controls
- Results list with expandable content
- Save-to-note functionality
- Cross-reference navigation

#### UI Patterns
- Tab-based main organization
- Multi-select for filtering
- Expandable result cards
- Score-based visual indicators

---

### 3. 🎙️ Podcasts Page

**Primary Function**: Podcast generation and management

#### Layout Structure
- **Tab-Based Interface**:
  - **"Episodes"** tab: Generated podcast management
  - **"Templates"** tab: Episode profile configuration

#### Key Features
- **Episode Management**:
  - Status-based grouping (Pending, Running, Completed, Failed)
  - Episode generation from notebook content
  - Audio playback and download
  - Episode deletion and regeneration

- **Profile Management**:
  - Episode profile creation and editing
  - Speaker configuration (1-4 speakers)
  - Voice and personality customization
  - Default profile initialization

#### Components
- Audio player for podcast playback
- Complex modal forms for profile editing
- Status indicators for episode states
- Speaker configuration panels
- Profile template system

#### UI Patterns
- Status-based content grouping
- Complex modal dialogs with multiple steps
- Fragment-based reactive forms
- Real-time status updates

---

### 4. 🤖 Models Page

**Primary Function**: AI provider and model configuration

#### Layout Structure
- **Sectioned Interface**:
  - Language Models section
  - Embedding Models section
  - Speech-to-Text Models section
  - Text-to-Speech Models section

#### Key Features
- **Model Configuration**:
  - Provider availability checking
  - Model selection with auto-save
  - Default model assignment
  - API key validation warnings

- **Provider Management**:
  - Multiple provider support (OpenAI, Anthropic, Groq, etc.)
  - Real-time availability checking
  - Contextual guidance and warnings

#### Components
- Model selector components
- Provider status indicators
- Auto-save form handling
- Warning and guidance messages

#### UI Patterns
- Sectioned layout by model type
- Consistent selection patterns
- Real-time validation feedback
- Progressive disclosure of options

---

### 5. 💱 Transformations Page

**Primary Function**: Content transformation prompt management

#### Layout Structure
- **Tab-Based Interface**:
  - **"Transformations"** tab: Prompt management
  - **"Playground"** tab: Testing interface

#### Key Features
- **Transformation Management**:
  - Custom prompt creation and editing
  - Default transformation templates
  - Playground for testing prompts
  - Import/export capabilities

- **Prompt Engineering**:
  - Rich text editor for prompts
  - Variable substitution support
  - Preview and testing functionality

#### Components
- Expandable transformation editors
- Monaco editor for prompt editing
- Test interface with live preview
- Import/export controls

#### UI Patterns
- Expandable card-based editing
- Rich text editing capabilities
- Split view for testing
- Template management system

---

### 6. ⚙️ Settings Page

**Primary Function**: Application configuration and preferences

#### Layout Structure
- **Sectioned Interface**:
  - Content Processing settings
  - File Management settings
  - Quality Settings section
  - Language Preferences

#### Key Features
- **Configuration Management**:
  - Processing engine selection
  - Auto-delete file options
  - Language preference settings
  - API key management

- **Help System**:
  - Expandable help sections for each setting
  - Contextual guidance
  - Warning messages for missing configurations

#### Components
- Configuration form controls
- Expandable help sections
- Warning and status indicators
- Language multi-select interface

#### UI Patterns
- Sectioned container organization
- Expandable help system
- Conditional warnings and guidance
- Auto-save configuration changes

---

## Shared Components and Utilities

### Core Components

#### 1. Model Selector (`components/model_selector.py`)
- **Purpose**: Reusable AI model selection interface
- **Features**: Provider filtering, model type filtering, custom formatting
- **Usage**: Used across multiple pages for consistent model selection

#### 2. Content Panels
- **Note Panel** (`components/note_panel.py`): Note editing and preview
- **Source Panel** (`components/source_panel.py`): Source content management
- **Source Insight Panel** (`components/source_insight.py`): Content insights display

#### 3. Stream App Utilities (`stream_app/`)
- **utils.py**: Page setup, session management, context building
- **auth.py**: Authentication handling
- **chat.py**: Chat functionality and session management
- **note.py**: Note creation and management
- **source.py**: Source management utilities

### Common UI Patterns

#### Layout Patterns
- **Column-based layouts**: Extensive use of multi-column layouts
- **Container organization**: Bordered containers for visual grouping
- **Modal dialogs**: `@st.dialog()` for complex forms and editing
- **Tab-based navigation**: Organizing related functionality

#### Form Elements
- **Text inputs**: Single-line and multi-line text input
- **Selection elements**: Dropdowns, multi-select, radio buttons
- **Specialized inputs**: File uploaders, number inputs, Monaco editor
- **Action buttons**: Icon-enhanced buttons with type classification

#### State Management
- **Session state**: Persistent state across page interactions
- **Fragment updates**: Isolated updates for performance
- **Auto-save patterns**: Immediate saving with user feedback
- **Context management**: Dynamic context building and tracking

#### Data Display
- **Card-based display**: Consistent card patterns with metadata
- **List rendering**: Dynamic lists with sorting and filtering
- **Status indicators**: Emoji and color-coded status representation
- **Progressive disclosure**: Expandable sections for complex content

---

## Authentication and Common Setup

### Page Setup Pattern
Every page uses a common setup function that handles:
- Authentication checking
- Model validation
- Database migration checking
- Version display
- Error handling

### Security Features
- Password protection for public deployments
- Session-based authentication
- API key management and validation

---

## Technical Requirements for React Migration

### Core Functionality to Replicate

#### State Management
- Global state for authentication and session
- Page-specific state management
- Context tracking and management
- Real-time updates for background processes

#### Component Architecture
- Reusable component library (model selectors, content panels)
- Modal system for complex forms
- Tab-based navigation components
- Card-based content display

#### Data Integration
- REST API integration for all CRUD operations
- Real-time updates for podcast generation status
- File upload and management
- Search and filtering capabilities

#### Advanced Features
- Monaco editor integration for markdown editing
- Audio player for podcast playback
- Drag-and-drop file uploads
- Context-aware help system

### Shadcn/UI Components Mapping

#### Layout Components
- **Layout**: App shell with sidebar navigation
- **Tabs**: For multi-view pages
- **Card**: For content display
- **Sheet/Dialog**: For modal forms and editing

#### Form Components
- **Input**: Text inputs and search fields
- **Textarea**: Multi-line text input
- **Select**: Dropdown selections
- **Button**: Action buttons with variants
- **Checkbox/Switch**: Boolean options
- **Slider**: Numeric ranges

#### Display Components
- **Badge**: Status indicators
- **Progress**: Loading states and progress bars
- **Separator**: Visual organization
- **Collapsible**: Expandable sections

#### Feedback Components
- **Toast**: User feedback and notifications
- **Alert**: Warnings and information
- **Skeleton**: Loading states

---

## Migration Priority and Phases

### Phase 1: Core Infrastructure
1. Authentication system
2. Navigation and routing
3. Basic page layouts
4. API integration layer

### Phase 2: Main Functionality
1. Notebooks page with three-column layout
2. Source and note management
3. Basic chat interface
4. Settings page

### Phase 3: Advanced Features
1. Search and AI querying
2. Podcast generation and management
3. Transformations system
4. Real-time updates and status tracking

### Phase 4: Polish and Optimization
1. Advanced UI interactions
2. Performance optimizations
3. Accessibility improvements
4. Mobile responsiveness enhancements

---

## Key Design Considerations

### User Experience
- Maintain the three-column layout for the main workspace
- Preserve the context control system
- Keep the modal-based editing workflow
- Ensure seamless navigation between pages

### Performance
- Implement efficient state management
- Optimize for large content lists
- Handle background processes gracefully
- Maintain responsive interactions

### Accessibility
- Keyboard navigation support
- Screen reader compatibility
- Clear visual hierarchy
- Appropriate contrast and sizing

### Responsive Design
- Mobile-first approach
- Collapsible navigation
- Adaptive column layouts
- Touch-friendly interactions

This migration guide provides a comprehensive foundation for transitioning from the current Streamlit implementation to a modern React/Shadcn-based interface while preserving all existing functionality and improving the overall user experience.