# Interface Overview

Open Notebook features a clean, intuitive interface designed to streamline your research workflow. This guide covers the layout, navigation, and interaction patterns to help you work efficiently with the platform.

## Interface Design Philosophy

Open Notebook follows a three-column layout inspired by Google Notebook LM but enhanced with additional features and customization options. The design prioritizes:

- **Workspace Organization**: Clear separation between content management and AI interaction
- **Context Awareness**: Visual indicators for what information is available to the AI
- **Privacy Control**: Granular control over data sharing with AI models
- **Streamlined Workflow**: Logical progression from source management to knowledge creation

## Three-Column Layout

### Main Workspace (Left Side)
The main workspace is divided into two columns that manage your research materials:

#### Sources Column (Left)
- **Add Source Button**: Quick access to add new research materials
- **Source Cards**: Visual representations of your documents, URLs, and other content
- **Context Indicators**: Visual cues showing whether sources are included in AI context
- **Source Actions**: Edit, delete, and transformation options for each source

#### Notes Column (Right)
- **Write a Note Button**: Create manual notes and observations
- **Note Cards**: Display both human-written and AI-generated notes
- **Note Types**: Visual distinction between manual and AI-generated content
- **Note Actions**: Edit, delete, and organization options

### Chat Interface (Right Side)
The chat interface provides AI interaction capabilities:

#### Chat Tab
- **Session Management**: Create, rename, and switch between conversation sessions
- **Message History**: Scrollable conversation history with the AI assistant
- **Context Display**: Shows what content is available to the AI (token count and character count)
- **Input Field**: Type questions and interact with your knowledge base

#### Podcast Tab
- **Episode Generation**: Create podcast episodes from your research materials
- **Profile Selection**: Choose from pre-configured episode profiles
- **Speaker Configuration**: Select and customize podcast speakers
- **Generation Controls**: Start podcast creation with custom instructions

## Navigation Structure

### Main Navigation
Open Notebook uses a page-based navigation system accessible through the sidebar:

- **📒 Notebooks**: Main workspace for research projects
- **🔍 Ask and Search**: Query your knowledge base across all notebooks
- **🎙️ Podcasts**: Manage podcast profiles and view generated episodes
- **🤖 Models**: Configure AI providers and model settings
- **💱 Transformations**: Create and manage content transformation prompts
- **⚙️ Settings**: Application configuration and preferences

### Notebook Navigation
Within each notebook:
- **Back to List**: Return to the notebook overview
- **Refresh**: Reload current notebook content
- **Notebook Header**: Edit name and description, archive/unarchive options
- **Session Controls**: Manage chat sessions and conversation history

## Settings and Preferences

### Location
Access settings through the **⚙️ Settings** page in the main navigation.

### Key Configuration Options

#### Content Processing
- **Document Engine**: Choose between auto, docling, or simple processing
- **URL Engine**: Select from auto, firecrawl, jina, or simple web scraping
- **Embedding Options**: Configure automatic content embedding for vector search

#### File Management
- **Auto-Delete Files**: Automatically remove uploaded files after processing
- **YouTube Languages**: Set preferred languages for transcript download

#### Quality Settings
- **Processing Accuracy**: Balance between speed and accuracy for different content types
- **API Integration**: Configure external service API keys for enhanced processing

## Context Control System

### Three-Level Context System
Open Notebook provides granular control over what information AI models can access:

#### Not in Context
- Sources and notes marked as "not in context" are invisible to the AI
- Useful for keeping sensitive or irrelevant information private
- Reduces API costs by limiting context size

#### Summary Only
- AI receives condensed summaries of the content
- Balances information access with cost optimization
- AI can request full content if needed for specific queries

#### Full Content
- AI has access to complete document text
- Provides maximum context for detailed analysis
- Higher API costs but most comprehensive responses

### Context Indicators
Visual indicators throughout the interface show:
- **Token Count**: Current context size in tokens
- **Character Count**: Total characters in context
- **Context Composition**: What sources and notes are included
- **Cost Estimation**: Approximate API usage for current context

## Mobile Responsiveness

### Responsive Design
Open Notebook is built with Next.js, providing:
- **Adaptive Layout**: Columns collapse and stack on smaller screens
- **Touch-Friendly**: Buttons and interactions optimized for mobile devices
- **Scrollable Interface**: All content accessible through touch scrolling

### Mobile Usage Patterns
- **Vertical Stacking**: Three-column layout becomes vertically stacked
- **Collapsible Sections**: Expandable areas to save screen space
- **Touch Navigation**: Tap-friendly buttons and controls
- **Readable Text**: Responsive text sizing for different screen sizes

### Mobile Limitations
- **Complex Interactions**: Some advanced features work better on desktop
- **File Upload**: Limited file management capabilities on mobile browsers
- **Multi-tasking**: Reduced ability to reference multiple sources simultaneously

## Customization Options

### Interface Customization
- **Sidebar State**: Collapsed or expanded sidebar based on preference
- **Page Layout**: Wide or narrow layout options
- **Theme**: Follows system theme preferences (light/dark)

### Content Customization
- **Transformation Prompts**: Create custom AI prompts for content analysis
- **Episode Profiles**: Configure podcast generation with custom speakers and styles
- **Model Selection**: Choose different AI models for different tasks

### Workflow Customization
- **Session Management**: Organize conversations by topic or project
- **Note Organization**: Manual and AI-assisted note creation
- **Source Processing**: Choose processing engines based on content type

## Common UI Patterns

### Action Buttons
- **Primary Actions**: Bold, colored buttons for main actions (Create, Save, Generate)
- **Secondary Actions**: Subtle buttons for supporting actions (Edit, Delete, Refresh)
- **Icon Buttons**: Symbolic representations for common actions (📝, 🔄, 🗑️)

### Status Indicators
- **Loading States**: Spinners and progress indicators during processing
- **Success Messages**: Toast notifications for completed actions
- **Error Handling**: Clear error messages with actionable suggestions
- **Warning States**: Alerts for missing configuration or potential issues

### Content Cards
- **Source Cards**: Preview, metadata, and action buttons for documents
- **Note Cards**: Content preview with creation date and type indicators
- **Message Cards**: Chat history with clear sender identification

### Expandable Sections
- **Context View**: Collapsible JSON view of AI context
- **Help Sections**: Expandable guidance for configuration options
- **Session History**: Collapsible list of previous conversations

## Interaction Patterns

### Content Management
1. **Add Source**: Click "Add Source" → Choose input method → Process content
2. **Create Note**: Click "Write a Note" → Enter content → Save
3. **Transform Content**: Select source → Choose transformation → Generate insight

### AI Interaction
1. **Set Context**: Select sources/notes for AI access
2. **Ask Question**: Type in chat input → Receive AI response
3. **Save Response**: Click "💾 New Note" to save AI responses

### Session Management
1. **Create Session**: Click "Create New Session" → Name session → Start chatting
2. **Switch Session**: Select from session list → Load conversation history
3. **Rename Session**: Edit session name → Save changes

### Content Discovery
1. **Search**: Use search page → Enter query → Review results
2. **Filter**: Choose search type (text/vector) → Specify content types
3. **Navigate**: Click search results → View source content

## Screenshots Reference

The following screenshots illustrate key interface elements:

- **New Notebook**: ![New Notebook](/assets/new_notebook.png) - Notebook creation interface
- **Add Source**: ![Add Source](/assets/add_source.png) - Source addition dialog
- **Source List**: ![Source List](/assets/asset_list.png) - Three-column layout with sources
- **Context Control**: ![Context](/assets/context.png) - Context management interface
- **Transformations**: ![Transformations](/assets/transformations.png) - Content transformation tools
- **Human Note**: ![Human Note](/assets/human_note.png) - Manual note creation
- **AI Note**: ![AI Note](/assets/ai_note.png) - AI-generated note saving
- **Podcast Interface**: ![Podcast](/assets/podcast_listen.png) - Podcast generation interface
- **Search**: ![Search](/assets/search.png) - Search and discovery interface

## Keyboard Shortcuts

Currently, Open Notebook relies primarily on mouse/touch interactions. Standard browser shortcuts apply:

- **Ctrl/Cmd + R**: Refresh page
- **Ctrl/Cmd + F**: Find text on page
- **Tab**: Navigate between form fields
- **Enter**: Submit forms and chat messages
- **Escape**: Close dialogs and expandable sections

## Performance Considerations

### Interface Responsiveness
- **Lazy Loading**: Content loads as needed to maintain performance
- **Caching**: Frequently accessed data is cached for faster loading
- **Optimized Rendering**: Efficient display of large document lists

### Resource Management
- **Context Limits**: Token count displays help manage API costs
- **Memory Usage**: Efficient handling of large documents and conversations
- **Network Optimization**: Minimal data transfer for interface updates

## Tips for Efficient Use

### Organization
- Use descriptive notebook names and descriptions
- Keep related sources together in the same notebook
- Create focused chat sessions for different research aspects

### Context Management
- Start with "Summary Only" context to save costs
- Use "Full Content" only when detailed analysis is needed
- Regular review and cleanup of unused sources

### Search Strategy
- Use specific keywords for text search
- Try vector search for conceptual queries
- Combine different search types for comprehensive results

### Workflow Optimization
- Create transformation prompts for recurring analysis tasks
- Use episode profiles for consistent podcast generation
- Organize notes by topic or research phase

This interface overview should help you navigate Open Notebook effectively and take advantage of its powerful features while maintaining control over your research data and AI interactions.