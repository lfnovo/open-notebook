# Sources Guide

Open Notebook serves as your central hub for research materials, supporting a wide variety of content formats. This guide covers everything you need to know about adding, managing, and organizing sources in your notebooks.

## Supported File Types and Formats

Open Notebook leverages the powerful [content-core](https://github.com/lfnovo/content-core) library to process various content types with intelligent engine selection.

### 📄 Documents
- **PDF** - Research papers, reports, books
- **EPUB** - E-books and digital publications
- **Microsoft Office**:
  - Word documents (.docx, .doc)
  - PowerPoint presentations (.pptx, .ppt)
  - Excel spreadsheets (.xlsx, .xls)
- **Text files** - Plain text (.txt), Markdown (.md)
- **HTML** - Web pages and HTML files

### 🎥 Media Files
- **Video formats**:
  - MP4, AVI, MOV, WMV
  - Automatic transcription to text
- **Audio formats**:
  - MP3, WAV, M4A, AAC
  - Speech-to-text conversion

### 🌐 Web Content
- **URLs** - Any web page, blog post, or article
- **YouTube videos** - Automatic transcript extraction
- **News articles** - Automatic content extraction

### 🖼️ Images
- **JPG, PNG, TIFF** - With OCR text recognition
- **Screenshots** - Perfect for capturing visual information

### 📦 Archives
- **ZIP, TAR, GZ** - Compressed file support

## Adding Sources Step-by-Step

### Method 1: Adding Links

1. **Navigate to your notebook**
2. **Click "Add Source"**
3. **Select "Link" option**
4. **Enter the URL** in the text field
5. **Configure options** (see Configuration Options below)
6. **Click "Process"**

**Examples:**
- Research articles: `https://arxiv.org/abs/2301.00001`
- YouTube videos: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
- News articles: `https://example.com/article`
- Blog posts: `https://blog.example.com/post`

### Method 2: Uploading Files

1. **Navigate to your notebook**
2. **Click "Add Source"**
3. **Select "Upload" option**
4. **Click "Choose File"** and select your document
5. **Configure options** (see Configuration Options below)
6. **Click "Process"**

**Supported formats:**
- Documents: PDF, DOCX, PPTX, XLSX, EPUB, TXT, MD
- Media: MP4, MP3, WAV, M4A (requires speech-to-text model)
- Images: JPG, PNG, TIFF (with OCR)
- Archives: ZIP, TAR, GZ

### Method 3: Adding Text Content

1. **Navigate to your notebook**
2. **Click "Add Source"**
3. **Select "Text" option**
4. **Paste or type your content** in the text area
5. **Configure options** (see Configuration Options below)
6. **Click "Process"**

**Use cases:**
- Meeting notes or transcripts
- Research findings
- Interview transcripts
- Code snippets or documentation

## Configuration Options

### Transformations
Apply AI-powered transformations to extract insights from your sources:

- **Summary** - Generate concise summaries
- **Key Points** - Extract main ideas and takeaways
- **Questions** - Generate questions for further research
- **Analysis** - Provide detailed analysis of content
- **Custom transformations** - Create your own prompts

### Embedding Options
Choose how content should be embedded for vector search:

- **Ask every time** - Prompt for each source
- **Always embed** - Automatically embed all sources
- **Never embed** - Skip embedding (can be done later)

**Note:** Embedding enables AI-powered search and context retrieval but uses tokens from your AI provider.

### File Management
- **Delete after processing** - Remove uploaded files from server after processing
- **Keep files** - Retain files on server (useful for archival)

## Source Management and Organization

### Viewing Source Details
Click the **"Expand"** button on any source to view:
- Full extracted content
- Generated insights (transformations)
- Processing metadata
- Embedded chunk information

### Context Configuration
Control how sources are included in AI conversations:

- **🚫 Not in Context** - Exclude from AI context
- **📄 Summary** - Include summary only (recommended)
- **📋 Full Content** - Include complete content (uses more tokens)

### Source Metadata
Each source includes:
- **Title** - Extracted or custom title
- **Topics** - Automatically detected or manually added tags
- **Created/Updated** - Timestamps for tracking
- **Embedded chunks** - Number of vector embeddings
- **Insights count** - Number of generated insights

### Searching Sources
Use the search functionality to find specific sources:
- **Text search** - Search titles and content
- **Vector search** - Semantic similarity search
- **Filter by notebook** - View sources from specific notebooks
- **Filter by type** - URLs, uploads, or text content

## Source Processing and Transformation

### Content Extraction Engines
Open Notebook uses intelligent engine selection:

- **Docling** - PDF and Office documents (default)
- **PyMuPDF** - Lightweight PDF processing
- **Firecrawl** - Enhanced web scraping
- **Jina** - Advanced content extraction
- **BeautifulSoup** - Standard web scraping

### Processing Workflow
1. **Upload/URL submission** - Source is received
2. **Engine selection** - Best extraction method chosen
3. **Content extraction** - Text and metadata extracted
4. **Transformation application** - AI insights generated
5. **Embedding creation** - Vector embeddings for search
6. **Storage** - Content saved to database

### Speech-to-Text Processing
For audio and video files:
1. **Audio extraction** - Video converted to audio
2. **Transcription** - Speech converted to text
3. **Content processing** - Standard text processing applied

**Requirements:**
- Speech-to-text model configured (OpenAI Whisper, etc.)
- Compatible audio/video format

## Best Practices

### Content Organization
- **Use descriptive titles** - Edit auto-generated titles for clarity
- **Add relevant topics** - Tag sources for better categorization
- **Group related sources** - Keep related materials in same notebook
- **Regular cleanup** - Remove outdated or irrelevant sources

### Performance Optimization
- **Selective embedding** - Only embed sources you'll search
- **Context management** - Use summary context when possible
- **Batch processing** - Add multiple sources at once
- **File cleanup** - Enable automatic file deletion

### Cost Management
- **Monitor token usage** - Track embedding and transformation costs
- **Use summary context** - Reduce token consumption in conversations
- **Selective transformations** - Only apply needed transformations
- **Provider selection** - Choose cost-effective AI providers

## Limitations and Considerations

### File Size Limits
- **Maximum upload size** - Depends on server configuration
- **Processing time** - Large files take longer to process
- **Memory usage** - Very large files may cause processing issues

### Format Limitations
- **Scanned PDFs** - May require OCR processing
- **Password-protected files** - Cannot be processed
- **Corrupted files** - Will fail processing gracefully
- **Proprietary formats** - Some formats may not be supported

### Language Support
- **YouTube transcripts** - Configurable preferred languages
- **Multi-language content** - Supported by AI models
- **OCR accuracy** - Varies by image quality and language

### Privacy and Security
- **File storage** - Temporary files deleted after processing
- **Content persistence** - Extracted text stored in database
- **AI processing** - Content sent to configured AI providers
- **Access control** - Password protection available

## Troubleshooting Source Issues

### Common Problems and Solutions

#### "Unsupported file type" error
**Solution:**
- Check the supported formats list above
- Ensure file is not corrupted
- Try converting to a supported format

#### "No transcript found" for YouTube videos
**Solution:**
- Verify video has captions/subtitles
- Check YouTube transcript language preferences
- Try manually uploading audio if available

#### "Processing failed" for documents
**Solution:**
- Ensure file is not password-protected
- Check file size (try smaller files)
- Verify file is not corrupted
- Try different processing engine in settings

#### "Audio/video upload disabled" warning
**Solution:**
- Configure speech-to-text model in Models
- Ensure provider API keys are set
- Check model availability

#### Embedding fails or takes too long
**Solution:**
- Check embedding model configuration
- Verify API key and quota limits
- Try processing without embedding first
- Check content length (very long content may fail)

### Getting Help
- **Check server logs** - Enable debug logging for detailed error info
- **GitHub Issues** - Report bugs or request features
- **Discord Community** - Get help from other users
- **Documentation** - Review setup and configuration guides

## Advanced Features

### Custom Transformations
Create your own AI-powered transformations:
1. Navigate to **Settings → Transformations**
2. Click **"Create New"**
3. Define your prompt template
4. Set default application preferences
5. Test with sample content

### Bulk Operations
- **Multiple file upload** - Select multiple files at once
- **Batch transformations** - Apply to multiple sources
- **Bulk embedding** - Process multiple sources for search

### API Integration
Use the REST API for programmatic source management:
- **Create sources** - `POST /api/sources`
- **List sources** - `GET /api/sources`
- **Get source details** - `GET /api/sources/{id}`
- **Update source** - `PUT /api/sources/{id}`
- **Delete source** - `DELETE /api/sources/{id}`

### Automation
- **Auto-embedding** - Configure default embedding behavior
- **Default transformations** - Apply specific transformations to all sources
- **File cleanup** - Automatic deletion of temporary files
- **Regular processing** - Schedule source updates

## Integration Examples

### Research Workflow
1. **Add research papers** (PDF uploads)
2. **Include relevant articles** (URL links)
3. **Add meeting notes** (text content)
4. **Apply analysis transformation** to extract insights
5. **Enable embedding** for cross-source search
6. **Use summary context** for efficient AI conversations

### Content Creation Workflow
1. **Gather reference materials** (mixed formats)
2. **Apply summary transformations** for quick overviews
3. **Extract key points** for outline creation
4. **Use full content context** for detailed writing
5. **Search across sources** for specific information

### Learning and Study Workflow
1. **Upload course materials** (PDFs, videos)
2. **Add supplementary articles** (web links)
3. **Create study notes** (text content)
4. **Apply question generation** for self-testing
5. **Use vector search** for concept lookup
6. **Generate summaries** for review

This comprehensive sources guide should help you make the most of Open Notebook's powerful content processing capabilities. Remember to experiment with different configurations to find the workflow that works best for your specific use case.