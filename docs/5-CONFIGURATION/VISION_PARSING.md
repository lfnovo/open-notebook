# Vision Parsing in Open Notebook

## Overview
Open Notebook now supports **Multimodal Vision Parsing** for document ingestion. This feature allows the system to extract high-quality text, understand complex layouts, describe scientific graphs, and interpret images within PDF files or standalone images (PNG, JPEG, WEBP) by utilizing Vision-Language Models (VLMs).

## How It Works

Instead of relying solely on traditional OCR tools (which often struggle with complex formatting, non-standard fonts, or charts), the system intercepts image and PDF uploads and routes them to a configured Vision Model.

1. **Format Identification**: The system detects the MIME type of the uploaded source (`.pdf`, `.jpg`, `.png`, etc.).
2. **Rasterization**: 
   - For images, the file is converted directly into a base64 string.
   - For PDFs, `PyMuPDF` (fitz) is used to rasterize each page at a high DPI (150). To prevent blocking the async event loop of the API, this CPU-intensive operation is delegated to `asyncio.to_thread`.
3. **Multimodal Invocation**: The base64 representation of the image is injected into a `langchain_core` `HumanMessage` payload using the standard dict format: `{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}`.
4. **LLM Parsing**: A detailed prompt instructs the VLM to extract text, describe graphs, and explain the context. The output is formatted in Markdown and concatenated.

## Provider-Agnostic Design

The Vision Parsing pipeline is designed to be fully agnostic of the backend provider. By strictly adhering to the LangChain `HumanMessage` standard, the system seamlessly supports:
- **Local Models (Privacy-First)**: Open-source multimodal models like `llava`, `gemma2-vision`, or `minicpm-v` running locally via Ollama.
- **Cloud Models**: Commercial APIs such as OpenAI (`gpt-4o`), Anthropic (`claude-3-5-sonnet-20240620`), or Google (`gemini-1.5-pro`).

## Configuration

To enable Vision Parsing:
1. Navigate to **Settings** -> **Models/API Keys** in the web UI.
2. Select your provider of choice (e.g., Ollama for local execution, or OpenAI for cloud execution).
3. Add a model and categorize it as **Vision**.
   - *Note for Docker/Linux users*: If you are running Open Notebook via Docker and Ollama on the host machine, set the endpoint to `http://host.docker.internal:11434` (or `http://172.17.0.1:11434`).
4. Set the newly added model as the **Default Vision Model**.

## Fallback Mechanism
If no Vision model is configured, or if an error occurs during API invocation, the system gracefully falls back to the standard text extraction methods provided by `content-core` (such as `pdfminer` or `pdfplumber`).
