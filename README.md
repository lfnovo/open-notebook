# Open Notebook

An open source, privacy-focused alternative to Google's Notebook LM. Why give Google more of our data when we can take control of our own research workflows?

In a world dominated by Artificial Intelligence, having the ability to think 🧠 and acquire new knowledge 💡, is a skill that should not be a privilege for a few, nor restricted to a single company.

Open Notebook empowers you to manage your research, generate AI-assisted notes, and interact with your content—on your terms.

Learn more about our project at [https://www.open-notebook.ai](https://www.open-notebook.ai)

## ⚙️ Setting Up

Go to the [Setup Guide](docs/SETUP.md) to learn how to set up the tool in details.

To setup with Docker/Portainer:

```yaml
version: '3'

services:
  surrealdb:
    image: surrealdb/surrealdb:v2
    ports:
      - "8000:8000"
    volumes:
      - surreal_data:/mydata
    command: start --log trace --user root --pass root rocksdb:/mydata/mydatabase.db
    pull_policy: always
    user: root

  open_notebook:
    image: lfnovo/open_notebook:latest
    ports:
      - "8080:8502"
    env_file:
      - ./docker.env
    depends_on:
      - surrealdb
    pull_policy: always

volumes:
  surreal_data:

```


## Usage Instructions

Go to the [Usage](docs/USAGE.md) page to learn how to use all features.

## Features

![New Notebook](docs/assets/asset_list.png)


- **Multi-Notebook Support**: Organize your research across multiple notebooks effortlessly.
- **Multi-model support**: Open AI, Anthropic, Gemini, Vertex AI, Open Router, Ollama.
- **Podcast Generator**: Automatically convert your notes into a podcast format.
- **Broad Content Integration**: Works with links, PDFs, EPUB, Office, TXT, Markdown files, YouTube videos, Audio files, Video files and pasted text.
- **AI-Powered Notes**: Write notes yourself or let the AI assist you in generating insights.
- **Integrated Search Engines**: Built-in full-text and vector search for faster information retrieval.
- **Fine-Grained Context Management**: Choose exactly what to share with the AI to maintain control.

## 🚀 New Features

### v0.0.7 - Model Management  🗂️

- Manage your AI models and providers in a single interface
- Define default models for several tasks such as chat, transformation, embedding, etc
- Enabled support for Embedding models from Gemini, Vertex and Ollama

### v0.0.6 - ePub and Office files support 📄

You can now process ePub and Office files (Word, Excel, PowerPoint), extracting text and insights from them. Perfect for books, reports, presentations, and more.

### v0.0.5 - Audio and Video support 📽️

You can now process audio and video files, extracting transcripts and insights from them. Perfect for podcasts, interviews, lectures, and more.

### v0.0.4 - Podcasts  🎙️

You can now build amazing custom podcasts based on your own data. Customize your speakers, episode structure, cadence, voices, etc. 

Check out a sample using my own voice created on Eleven Labs and a interview format. 

[![Check out our podcast sample](https://img.youtube.com/vi/MSGtUFohft0/0.jpg)](https://www.youtube.com/watch?v=MSGtUFohft0)

You can generate your podcast in dozens of languages.

Head to the [Podcasts](docs/PODCASTS.md) page for more info

### v0.0.3 - Transformations ✨

We just release a much more powerful way to create more value from your sources.
Transformations enable you do extract an unlimited amount of insights from your content.
It's 100% customizable and you can extend it to your own needs, like Paper Analysis, Article Writing, etc.

Head to the [Transformations](docs/TRANSFORMATIONS.md) page for more info

### v0.0.2 - Several new providers are supported now:

- OpenAI
- Anthropic
- Open Router
- LiteLLM
- Vertex AI
- Ollama

### 📝 Notebook Page

Three intuitive columns to streamline your work:
1. **Sources**: Manage all research materials.
2. **Notes**: Create or AI-generate notes.
3. **Chat**: Chat with the AI, leveraging your content.

### ⚙️ Context Configuration

Take control of your data. Decide what gets sent to the AI with three context options:
- No context
- Summary only
- Full content

Plus, you can add your project description to help the AI provide more accurate and helpful responses.

### 🔍 Integrated Search for Your Items

Locate anything across your research with ease using full-text and vector-based search.

### 💬 Powerful open prompts

Jinja based prompts that are easy to customize to your own preferences.


## 🌟 Roadmap

- **Enhanced Citations**: Improved layout and finer control for citations.
- **Better Embeddings & Summarization**: Smarter ways to distill information.
- **Multiple Chat Sessions**: Juggle different discussions within the same notebook.
- **Live Front-End Updates**: Real-time UI updates for a smoother experience.
- **Async Processing**: Faster UI through asynchronous content processing.
- **Cross-Notebook Sources and Notes**: Reuse research notes across projects.
- **Bookmark Integration**: Integrate with your favorite bookmarking app.
- **Multi-model support**: Open AI, Anthropic, Vertex AI, Open Router, Ollama, etc. ✅ 0.0.2
- **Insight Generation**: New tools for creating insights - [transformations](docs/TRANSFORMATIONS.md) ✅ 0.0.3
- **Podcast Generator**: Automatically convert your notes into a podcast format.  ✅ 0.0.4


## 💻 Tech Stack

- **Streamlit**: For the front-end (Looking to move out of Streamlit. Contributors welcome!).
- **SurrealDB**: Fast, scalable database solution.
- **Langchain/Langgraph**: The backbone for LLM interactions.
- **Podcastfy**: For generating podcasts from your notes.


## 🙌 Help Wanted

We would love your contributions! Specifically, we're looking for help with:
- **Front-End Development**: Improve the UI/UX by moving beyond Streamlit.
- **Testing & Bug Fixes**: Help make Open Notebook more robust.
- **Feature Development**: Let’s make the coolest note-taking tool together!

See more at [CONTRIBUTING](CONTRIBUTING.md)
## 📄 License

Open Notebook is MIT licensed. See the [LICENSE](LICENSE) file for details.

---

Your contributions, feature requests, and bug reports are always welcome. Let's build a research tool that respects our privacy and makes learning truly open for everyone. ✨

---

This project uses the following third-party libraries:

- [Podcastfy](https://github.com/souzatharsis/podcastfy) - Licensed under the Apache License 2.0