# Open Notebook

An open source, privacy-focused alternative to Google's Notebook LM. Why give Google more of our data when we can take control of our own research workflows?

In a world dominated by Artificial Intelligence, having the ability to think 🧠 and acquire new knowledge 💡, is a skill that should not be a privilege for a few, nor restricted to a single company.

Open Notebook empowers you to manage your research, generate AI-assisted notes, and interact with your content—on your terms.

## ⚙️ Setting Up

Go to the [Setup Guide](docs/SETUP.md) to learn how to set up the tool in details.

But, the gist of it is: 

```sh
git clone https://github.com/lfnovo/open_notebook.git
cd open_notebook
cp .env.sample .env
poetry install
poetry run streamlit run app_home.py
```

or with docker:

```yaml
services:
  surrealdb:
    image: surrealdb/surrealdb:v2
    ports:
      - "8000:8000"
    volumes:
      - ./surreal-data:/mydata
    user: "${UID}:${GID}"
    command: start --log trace --user root --pass root rocksdb:mydatabase.db
    pull_policy: always
  open_notebook:
    image: lfnovo/open_notebook:latest
    ports:
      - "8080:8502"
    volumes:
      - ./docker.env:/app/.env
    depends_on:
      - surrealdb
    pull_policy: always
```



## Usage Instructions

Go to the [Usage](docs/USAGE.md) page to learn how to use all features.

## Features

![New Notebook](docs/assets/asset_list.png)


- **Multi-Notebook Support**: Organize your research across multiple notebooks effortlessly.
- **Broad Content Integration**: Works with links, PDFs, TXT files, PowerPoint presentations, YouTube videos, and pasted text (audio/video support coming soon).
- **AI-Powered Notes**: Write notes yourself or let the AI assist you in generating insights.
- **Recursive Summarization**: Tackle large content by recursively summarizing it.
- **Integrated Search Engines**: Built-in full-text and vector search for faster information retrieval.
- **Fine-Grained Context Management**: Choose exactly what to share with the AI to maintain control.
- **Cost Estimation**: Estimate costs for large context processing to keep budget control in check.

## 🚀 New Features

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




## 🌟 Coming Soon

- **Podcast Generator**: Automatically convert your notes into a podcast format.
- **Multi-model support**: Anthropic, Gemini, Mistral, Ollama coming soon.
- **Enhanced Citations**: Improved layout and finer control for citations.
- **Insight Generation**: New tools for creating insights, leveraging the Fabric framework.
- **Better Embeddings & Summarization**: Smarter ways to distill information.
- **Multiple Chat Sessions**: Juggle different discussions within the same notebook.
- **Live Front-End Updates**: Real-time UI updates for a smoother experience.
- **Async Processing**: Faster UI through asynchronous content processing.
- **Improved Error Handling**: Making everything more robust.
- **Cross-Notebook Sources and Notes**: Reuse research notes across projects.
- **Bookmark Integration**: Integrate with your favorite bookmarking app.


## 💻 Tech Stack

- **Streamlit**: For the front-end (Looking to move out of Streamlit. Contributors welcome!).
- **SurrealDB**: Fast, scalable database solution.
- **Langchain/Langgraph**: The backbone for LLM interactions.


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
