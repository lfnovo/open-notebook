//! PDF processing and text extraction

use anyhow::{Context, Result};
use std::path::Path;

use crate::core::document::{Document, DocumentMetadata, SourceType};

/// PDF processor for extracting text from PDF files
pub struct PdfProcessor {
    // Configuration options could go here
}

impl PdfProcessor {
    pub fn new() -> Self {
        Self {}
    }

    /// Process a PDF file and extract text
    pub async fn process(&self, path: &Path) -> Result<Document> {
        let path = path.to_path_buf();

        // Run PDF extraction in blocking task
        let (text, metadata) = tokio::task::spawn_blocking(move || {
            Self::extract_pdf_content(&path)
        })
        .await?
        .context("Failed to extract PDF content")?;

        let title = path
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("Untitled")
            .to_string();

        let mut doc = Document::new(title, text, SourceType::Pdf);
        doc.metadata = metadata;
        doc.source_url = Some(format!("file://{}", path.display()));

        Ok(doc)
    }

    fn extract_pdf_content(path: &Path) -> Result<(String, DocumentMetadata)> {
        use lopdf::Document as PdfDocument;

        let pdf = PdfDocument::load(path).context("Failed to load PDF")?;

        // Extract text from all pages
        let mut text = String::new();
        let pages = pdf.get_pages();

        for (page_num, _) in pages.iter() {
            if let Ok(page_text) = pdf.extract_text(&[*page_num]) {
                text.push_str(&page_text);
                text.push('\n');
            }
        }

        // Extract metadata
        let metadata = DocumentMetadata {
            page_count: Some(pages.len()),
            word_count: Some(text.split_whitespace().count()),
            ..Default::default()
        };

        Ok((text, metadata))
    }

    /// Process multiple PDFs in a directory
    pub async fn process_directory(&self, dir: &Path) -> Result<Vec<Document>> {
        let mut documents = Vec::new();

        let entries = std::fs::read_dir(dir).context("Failed to read directory")?;

        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().map(|e| e == "pdf").unwrap_or(false) {
                match self.process(&path).await {
                    Ok(doc) => documents.push(doc),
                    Err(e) => tracing::warn!(path = %path.display(), error = %e, "Failed to process PDF"),
                }
            }
        }

        Ok(documents)
    }
}

impl Default for PdfProcessor {
    fn default() -> Self {
        Self::new()
    }
}
