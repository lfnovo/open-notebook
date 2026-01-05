# Adding Sources - Getting Content Into Your Notebook

Sources are the raw materials of your research. This guide covers how to add different types of content.

---

## Quick-Start: Add Your First Source

### Option 1: Upload a File (PDF, Word, etc.)

```
1. In your notebook, click "Add Source"
2. Select "Upload File"
3. Choose a file from your computer
4. Click "Upload"
5. Wait 30-60 seconds for processing
6. Done! Source appears in your notebook
```

### Option 2: Add a Web Link

```
1. Click "Add Source"
2. Select "Web Link"
3. Paste URL: https://example.com/article
4. Click "Add"
5. Wait for processing (usually faster than files)
6. Done!
```

### Option 3: Paste Text

```
1. Click "Add Source"
2. Select "Text"
3. Paste or type your content
4. Click "Save"
5. Done! Immediately available
```

---

## Supported File Types

### Documents
- **PDF** (.pdf) — Best support, including scanned PDFs with OCR
- **Word** (.docx, .doc) — Full support
- **PowerPoint** (.pptx) — Slides converted to text
- **Excel** (.xlsx, .xls) — Spreadsheet data
- **EPUB** (.epub) — eBook files
- **Markdown** (.md, .txt) — Plain text formats
- **HTML** (.html, .htm) — Web page files

**File size limits:** Up to ~100MB (varies by system)

**Processing time:** 10 seconds - 2 minutes (depending on length and file type)

### Audio & Video
- **Audio**: MP3, WAV, M4A, OGG, FLAC (~30 seconds - 3 minutes per hour)
- **Video**: MP4, AVI, MOV, MKV, WebM (~3-10 minutes per hour)
- **YouTube**: Direct URL support
- **Podcasts**: RSS feed URL

**Automatic transcription**: Audio/video is transcribed to text automatically. This requires enabling speech-to-text in settings.

### Web Content
- **Articles**: Blog posts, news articles, Medium
- **YouTube**: Full videos or playlists
- **PDFs online**: Direct PDF links
- **News**: News site articles

**Just paste the URL** in "Web Link" section.

### What Doesn't Work
- Paywalled content (WSJ, FT, etc.) — Can't extract
- Password-protected PDFs — Can't open
- Pure image files (.jpg, .png) — Except scanned PDFs which have OCR
- Very large files (>100MB) — Timeout

---

## What Happens When You Add a Source

The system automatically does four things:

```
1. EXTRACT TEXT
   File/URL → Readable text
   (PDFs get OCR if scanned)
   (Videos get transcribed if enabled)

2. BREAK INTO CHUNKS
   Long text → ~500-word pieces
   (So search finds specific parts, not whole document)

3. CREATE EMBEDDINGS
   Each chunk → Vector representation
   (Enables semantic/concept search)

4. INDEX & STORE
   Everything → Database
   (Ready to search and retrieve)
```

**Time to use:** After the progress bar completes, the source is ready immediately. Embeddings are created in the background.

---

## Step-by-Step for Different Types

### PDFs

**Best practices:**
```
Clean PDFs:
  1. Upload → Done
  2. Processing time: ~30-60 seconds

Scanned/Image PDFs:
  1. Upload same way
  2. System auto-detects and uses OCR
  3. Processing time: ~2-3 minutes
  4. (Higher, due to OCR overhead)

Large PDFs (50+ pages):
  1. Consider splitting into smaller files
  2. Or upload as-is (system handles it)
  3. Processing time scales with size
```

**Common issues:**
- "Can't extract text" → PDF is corrupted or has copy protection
- Solution: Try opening in Adobe. If it won't, the PDF is likely protected.

### Web Links / Articles

**Best practices:**
```
1. Copy full URL from browser: https://example.com/article-title
2. Paste in "Web Link"
3. Click Add
4. Wait for extraction

Processing time: Usually 5-15 seconds
```

**What works:**
- Standard web articles
- Blog posts
- News articles
- Wikipedia pages
- Medium posts
- Substack articles

**What doesn't work:**
- Twitter threads (unreliable)
- Paywalled articles (can't access)
- JavaScript-heavy sites (content not extracted)

**Pro tip:** If it doesn't work, copy the article text and paste as "Text" instead.

### Audio Files

**Best practices:**
```
1. Ensure speech-to-text is enabled in Settings
2. Upload MP3, WAV, or M4A file
3. System automatically transcribes to text
4. Processing time: ~1 minute per 5 minutes of audio

Example:
  - 1-hour podcast → 12 minutes processing
  - 10-minute recording → 2 minutes processing
```

**Quality matters:**
- Clear audio: Fast transcription
- Muffled/noisy audio: Slower, less accurate transcription
- Background noise: Try to minimize before uploading

**Tip:** If audio quality is poor, the AI might misinterpret content. You can manually correct transcription if needed.

### YouTube Videos

**Best practices:**
```
Two ways to add:

Method 1: Direct URL
  1. Copy YouTube URL: https://www.youtube.com/watch?v=...
  2. Paste in "Web Link"
  3. Click Add
  4. System extracts captions (if available) + transcript

Method 2: Playlist
  1. Paste playlist URL
  2. System adds all videos as separate sources
  3. Each video processed separately
  4. Takes longer (multiple videos)
```

**What's extracted:**
- Captions/subtitles (if available)
- Transcription (if captions aren't available)
- Basic metadata (title, channel, length)

**Processing:**
- 10-minute video: ~2-3 minutes
- 1-hour video: ~10-15 minutes

### Text / Paste Content

**Best practices:**
```
1. Select "Text" when adding source
2. Paste or type content
3. System processes immediately
4. No wait time needed

Good for:
  - Notes you want to reference
  - Quotes from books
  - Transcripts you have handy
  - Quick research snippets
```

---

## Managing Your Sources

### Viewing Source Details

```
Click on source → See:
  - Original file name/title
  - When it was added
  - Size and format
  - Processing status
  - Number of chunks
```

### Organizing with Metadata

You can add to each source:
- **Title**: Better name than original filename
- **Tags**: Category labels ("primary research", "background", "competitor analysis")
- **Description**: A few notes about what it contains

**Why this matters:**
- Makes sources easier to find
- Helps when contextualizing for Chat
- Useful for organizing large notebooks

### Searching Within Sources

```
After sources are added, you can:

Text search: "Find exact phrase"
Vector search: "Find conceptually similar"

Both search across all sources in notebook.
Results show:
  - Which source
  - Which section
  - Relevance score
```

---

## Context Management: How Sources Get Used

You control how AI accesses sources:

### Three Levels (for Chat)

**Full Content:**
```
AI sees: Complete source text
Cost: 100% of tokens
Use when: Analyzing in detail, need precise citations
Example: "Analyze this methodology paper closely"
```

**Summary Only:**
```
AI sees: AI-generated summary (not full text)
Cost: ~10-20% of tokens
Use when: Background material, reference context
Example: "Use this as context but focus on the main source"
```

**Not in Context:**
```
AI sees: Nothing (excluded)
Cost: 0 tokens
Use when: Confidential, not relevant, or archived
Example: "Keep this in notebook but don't use in this conversation"
```

### How to Set Context (in Chat)

```
1. Go to Chat
2. Click "Select Context Sources"
3. For each source:
   - Toggle ON/OFF (include/exclude)
   - Choose level (Full/Summary/Excluded)
4. Click "Save"
5. Now chat uses these settings
```

---

## Common Mistakes

| Mistake | What Happens | How to Fix |
|---------|--------------|-----------|
| Upload 200 sources at once | System gets slow, processing stalls | Add 10-20 at a time, wait for processing |
| Use full content for all sources | Token usage skyrockets, expensive | Use "Summary" or "Excluded" for background material |
| Add huge PDFs without splitting | Processing is slow, search results less precise | Consider splitting large PDFs into chapters |
| Forget source titles | Can't distinguish between similar sources | Rename sources with descriptive titles right after uploading |
| Don't tag sources | Hard to find and organize later | Add tags immediately: "primary", "background", etc. |
| Mix languages in one source | Transcription/embedding quality drops | Keep each language in separate sources |
| Use same source multiple times | Takes up space, creates confusion | Add once; reuse in multiple chats/notebooks |

---

## Processing Status & Troubleshooting

### What the Status Indicators Mean

```
🟡 Processing
  → Source is being extracted and embedded
  → Wait 30 seconds - 3 minutes depending on size
  → Don't use in Chat yet

🟢 Ready
  → Source is processed and searchable
  → Can use immediately in Chat
  → Can apply transformations

🔴 Error
  → Something went wrong
  → Common reasons:
    - Unsupported file format
    - File too large or corrupted
    - Network timeout

⚪ Not in Context
  → Source added but excluded from Chat
  → Still searchable, not sent to AI
```

### Common Errors & Solutions

**"Unsupported file type"**
- You tried to upload a format not in the list (e.g., `.webp` image)
- Solution: Convert to supported format (PDF for documents, MP3 for audio)

**"Processing timeout"**
- Very large file (>100MB) or very long audio
- Solution: Split into smaller pieces or try uploading again

**"Transcription failed"**
- Audio quality too poor or language not detected
- Solution: Re-record with better quality, or paste text transcript manually

**"Web link won't extract"**
- Website blocks automated access or uses JavaScript for content
- Solution: Copy the article text and paste as "Text" instead

---

## Tips for Best Results

### For PDFs
- Clean, digital PDFs work best
- Remove copy protection if present (legally)
- Scanned PDFs work but take longer

### For Web Articles
- Use full URL including domain
- Avoid cookie/popup-laden sites
- If extraction fails, copy-paste text instead

### For Audio
- Clear, well-recorded audio transcribes better
- Remove background noise if possible
- YouTube videos usually have good transcriptions built-in

### For Large Documents
- Consider splitting into smaller sources
- Gives more precise search results
- Processing is faster for smaller pieces

### For Organization
- Name sources clearly (not "document_2.pdf")
- Add tags immediately after uploading
- Use descriptions for complex documents

---

## What Comes After: Using Your Sources

Once you've added sources, you can:

- **Chat** → Ask questions (see [Chat Effectively](chat-effectively.md))
- **Search** → Find specific content (see [Search Effectively](search.md))
- **Transformations** → Extract structured insights (see [Working with Notes](working-with-notes.md))
- **Ask** → Get comprehensive answers (see [Search Effectively](search.md))
- **Podcasts** → Turn into audio (see [Creating Podcasts](creating-podcasts.md))

---

## Summary Checklist

Before adding sources, confirm:

- [ ] File is in supported format
- [ ] File is under 100MB (or splitting large ones)
- [ ] Web links are full URLs (not shortened)
- [ ] Audio files have clear speech (if transcription-dependent)
- [ ] You've named source clearly
- [ ] You've added tags for organization
- [ ] You understand context levels (Full/Summary/Excluded)

Done! Sources are now ready for Chat, Search, Transformations, and more.
