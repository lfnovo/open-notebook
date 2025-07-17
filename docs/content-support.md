# Content Integration

Open Notebook provides comprehensive support for various content formats, making it your central hub for all research materials.

<div class="content-types-grid">
  <div class="content-card">
    <div class="content-icon">📄</div>
    <h3>Documents</h3>
    <ul>
      <li>PDF, Epub</li>
      <li>Text, Markdown</li>
      <li>Office files</li>
    </ul>
  </div>

  <div class="content-card">
    <div class="content-icon">🎥</div>
    <h3>Media</h3>
    <ul>
      <li>YouTube videos</li>
      <li>Local video files</li>
      <li>Audio recordings</li>
    </ul>
  </div>

  <div class="content-card">
    <div class="content-icon">🌐</div>
    <h3>Web Content</h3>
    <ul>
      <li>Web articles</li>
      <li>Blog posts</li>
      <li>News articles</li>
    </ul>
  </div>
</div>

## How each content is processed

### Link Processing

Add a URL to any website and the tool will scrape its content for you. This can be done through a simple HTTP request or through more powerful tools like Firecrawl or Jina.

### Youtube Transcripts

Add a URL for an Youtube video and we'll extract the transcript.

### PDF, DOC, PPT, ePub

Those documents will be processed and their text extract. This is done using [Docling](https://docling-project.github.io/) by default, by can  be changed to a light-weight alternative, if needed.

**Roadmap:** improvements to tables in PDFs and use of Vision model for images

### Video / Audio processing

Videos are converted to audio files before processing.
Audio files are processed for transcript extraction and the transcript text is saved.

**Roadmap:** We might add support for Gemini video understanding capabilities at some point.

:::info More Formats Coming Soon
We're constantly working on adding support for more content types and formats. Have a specific format in mind? [Share your suggestions](https://github.com/lfnovo/open_notebook/discussions/categories/ideas) in our GitHub discussions!
:::

## Embeddings

When you upload new content to the platform, you have the option to enable embedding for that content. This will trigger a process that consists of generating chunks of 1000 words and embedding them using the model of your choice. This enables the content to appear in searches when the model is doing research for you through the [Ask feature](/features/search.html). 

Although this is not necessary for you to use the app, it will greatly improve your experience and it is pretty cheap to use. 

- text-embedding-3-small (Open AI): $0.020 / 1M tokens
- text-embedding-004 (Gemini): $0.012 / 1M tokens - large free tier available
- free with Ollama models, like mxbai-embed-large

<style scoped>
.content-types-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
  margin: 2rem 0;
}

.content-card {
  background: var(--vp-c-bg-soft);
  border-radius: 12px;
  padding: 1.5rem;
  border: 1px solid var(--vp-c-divider);
  transition: transform 0.2s, box-shadow 0.2s;
}

.content-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.content-icon {
  font-size: 2.5rem;
  margin-bottom: 1rem;
  text-align: center;
}

.content-card h3 {
  margin: 0.5rem 0;
  color: var(--vp-c-brand);
  text-align: center;
}

.content-card ul {
  list-style: none;
  padding: 0;
  margin: 1rem 0 0;
}

.content-card ul li {
  padding: 0.3rem 0;
  text-align: center;
}

@media (max-width: 768px) {
  .content-types-grid {
    grid-template-columns: 1fr;
  }
}
</style>