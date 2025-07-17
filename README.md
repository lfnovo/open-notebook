<a id="readme-top"></a>

<!-- [![Contributors][contributors-shield]][contributors-url] -->
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
<!-- [![LinkedIn][linkedin-shield]][linkedin-url] -->


<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/lfnovo/open-notebook">
    <img src="docs/assets/hero.svg" alt="Logo">
  </a>

  <h3 align="center">Open Notebook</h3>

  <p align="center">
    An open source, privacy-focused alternative to Google's Notebook LM!
    <br /><strong>Join our <a href="https://discord.gg/37XJPXfz2w">Discord server</a> for help, to share workflow ideas, and suggest features!</strong>
    <br />
    <a href="https://www.open-notebook.ai"><strong>Checkout our website »</strong></a>
    <br />
    <br />
    <a href="https://www.open-notebook.ai/get-started.html">Get Started (Setup)</a>
    ·
    <a href="https://www.open-notebook.ai/features.html">Features</a>
  </p>
</div>


## 📢 Open Notebook is under very active development

> Open Notebook is under active development! We're moving fast and making improvements every week. Your feedback is incredibly valuable to me during this exciting phase and it gives me motivation to keep improving and building this amazing tool. Please feel free to star the project if you find it useful, and don't hesitate to reach out with any questions or suggestions. I'm excited to see how you'll use it and what ideas you'll bring to the project! Let's build something amazing together! 🚀

## Installation Issues?

> We have a CustomGPT built to help you install Open Notebook. [Check it out here](https://chatgpt.com/g/g-68776e2765b48191bd1bae3f30212631-open-notebook-installation-assistant). It will help you through each step of the process.

> There are also some [basic docker/openai installation guide](setup_guide/README.md) available if you prefer to install it manually.

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#setting-up">Setting Up</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
        <li><a href="#password-protection-optional">Password Protection</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#features">Features</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

![New Notebook](docs/assets/asset_list.png)


An open source, privacy-focused alternative to Google's Notebook LM. Why give Google more of our data when we can take control of our own research workflows?

In a world dominated by Artificial Intelligence, having the ability to think 🧠 and acquire new knowledge 💡, is a skill that should not be a privilege for a few, nor restricted to a single provider.

Open Notebook empowers you to manage your research, generate AI-assisted notes, and interact with your content—on your terms.

Learn more about our project at [https://www.open-notebook.ai](https://www.open-notebook.ai)



<p align="right">(<a href="#readme-top">back to top</a>)</p>



### Built With

[![Python][Python]][Python-url] [![SurrealDB][SurrealDB]][SurrealDB-url] [![LangChain][LangChain]][LangChain-url] [![Streamlit][Streamlit]][Streamlit-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>


## ⚙️ Setting Up

Go to the [Setup Guide](docs/SETUP.md) to learn how to set up the tool in details.

📚 **Need help choosing AI models?** Check out our [Model Selection Guide](https://github.com/lfnovo/open-notebook/blob/main/docs/models.md) for recommended combinations and provider comparisons.

You don't need to clone this repo if you just want to use the app without building from source! 
Take a look at the [Open Notebook Boilerplate](https://github.com/lfnovo/open-notebook-boilerplate) repo with a sample of how to set it up for maximum feature usability. 

### Running from source

Start by cloning this repo and cd into it.

```bash
git clone https://github.com/lfnovo/open-notebook
cd open-notebook
```

Rename `.env.example` into `.env` and set up your API keys.
Also, repeat the process for `docker.env` if you plan to run this using docker.

```bash
cp .env.example .env
cp .env.example docker.env
```

Edit .env for your API keys.

### 🔐 Password Protection (Optional)

For users hosting Open Notebook publicly (e.g., on PikaPods, cloud services), you can protect your instance with a password:

```bash
# Add this to your .env file
OPEN_NOTEBOOK_PASSWORD=your_secure_password_here
```

When this environment variable is set:
- **Streamlit UI**: Users must enter the password on first access
- **REST API**: All API calls require the password in the Authorization header (`Authorization: Bearer your_password`)
- **Local Usage**: If not set, no authentication is required (default behavior)

**API Usage with Password:**
```bash
# Example API call with password
curl -H "Authorization: Bearer your_password" http://localhost:5055/api/notebooks
```

This provides basic protection for public deployments while keeping local usage simple and password-free.

📚 **For detailed security information, see the [Security Guide](docs/security.md)**.

### 🚀 Quick Start

After setting up your environment, simply run:

```bash
make start-all
```

This single command will start all required services (database, API, worker, and UI) for you!

### System Dependencies

This project requires some system dependencies:

```bash
# macOS
brew install libmagic

# Ubuntu/Debian
sudo apt-get install libmagic-dev

# Fedora/RHEL/CentOS
sudo dnf install file-devel
```

### Installing Python Dependencies

Install all required Python packages:

```bash
uv sync
uv pip install python-magic
```

### Running the Application

Open Notebook now requires **four services** to run: the database, API backend, worker, and Streamlit interface.

#### ✨ Easiest Way: Use `make start-all`

After completing the setup above, the recommended way to run Open Notebook is:

```bash
make start-all
```

This single command will:
- Start **SurrealDB** database on port 8000
- Start **FastAPI** backend on port 5055  
- Start **Background Worker** for podcast generation and transformations
- Start **Streamlit UI** on port 8502

Once running, access Open Notebook at `http://localhost:8502` 🎉

#### Manual Setup (Development)

If you prefer to start services individually:

```bash
# 1. Start SurrealDB database
make database
# or: docker compose up -d surrealdb

# 2. Start the FastAPI backend (in terminal 1)
make api
# or: uv run --env-file .env uvicorn api.main:app --host 0.0.0.0 --port 5055

# 3. Start the background worker (in terminal 2)
make worker
# or: uv run --env-file .env surreal-commands-worker --import-modules commands

# 4. Start Streamlit UI (in terminal 3)
make run
# or: uv run --env-file .env streamlit run app_home.py
```

#### Service Endpoints
- **Streamlit UI**: `http://localhost:8502`
- **REST API**: `http://localhost:5055`
- **API Documentation**: `http://localhost:5055/docs` (Interactive Swagger UI)
- **SurrealDB**: `http://localhost:8000`

#### Service Management

```bash
# Check if all services are running
make status

# Stop all services
make stop-all

# Restart worker only
make worker-restart
```

**Note**: The worker is required for podcast generation and content transformations. Without it, these features will queue jobs but not process them.

## Provider Support Matrix

Thanks to the [Esperanto](https://github.com/lfnovo/esperanto) library, we support this providers out of the box!

| Provider     | LLM Support | Embedding Support | Speech-to-Text | Text-to-Speech |
|--------------|-------------|------------------|----------------|----------------|
| OpenAI       | ✅          | ✅               | ✅             | ✅             |
| Anthropic    | ✅          | ❌               | ❌             | ❌             |
| Groq         | ✅          | ❌               | ✅             | ❌             |
| Google (GenAI) | ✅          | ✅               | ❌             | ✅             |
| Vertex AI    | ✅          | ✅               | ❌             | ✅             |
| Ollama       | ✅          | ✅               | ❌             | ❌             |
| Perplexity   | ✅          | ❌               | ❌             | ❌             |
| ElevenLabs   | ❌          | ❌               | ✅             | ✅             |
| Azure OpenAI | ✅          | ✅               | ❌             | ❌             |
| Mistral      | ✅          | ✅               | ❌             | ❌             |
| DeepSeek     | ✅          | ❌               | ❌             | ❌             |
| Voyage       | ❌          | ✅               | ❌             | ❌             |
| xAI          | ✅          | ❌               | ❌             | ❌             |
| OpenRouter   | ✅          | ❌               | ❌             | ❌             |

### Common Issues and Solutions

If you encounter a port already in use error:
```
Port 8502 is already in use
```

Find and stop the running process:
```bash
# Find the process using port 8502
lsof -i :8502

# Kill the process (replace PID with the actual process ID)
kill -9 PID
```

Or specify a different port:
```bash
uv run --env-file .env streamlit run app_home.py --server.port=8503
```

### Running with Docker

Open Notebook offers two Docker deployment options:

#### Option 1: Multi-Container (Default)
If you prefer separate containers for each service:

```bash
# Run the full stack (SurrealDB + Streamlit + API)
docker compose --profile multi up
```

#### Option 2: Single-Container (Recommended for Simple Deployments)
For platforms like PikaPods or if you prefer an all-in-one solution:

```bash
# Run everything in a single container
docker compose -f docker-compose.single.yml up -d
```

Or directly:

```bash
docker run -d \
  --name open-notebook \
  -p 8502:8502 -p 5055:5055 \
  -v ./notebook_data:/app/data \
  -v ./surreal_single_data:/mydata \
  -e OPENAI_API_KEY=your_key \
  lfnovo/open_notebook:latest-single
```

Both setups provide:
- **Streamlit UI**: `http://localhost:8502`
- **REST API**: `http://localhost:5055`
- **API Documentation**: `http://localhost:5055/docs` (Interactive Swagger UI)

**📚 For detailed single-container deployment instructions, see the [Single-Container Deployment Guide](docs/single-container-deployment.md)**.

**Docker with Password Protection:**
To enable password protection in Docker, add `OPEN_NOTEBOOK_PASSWORD=your_password` to your environment variables.

### API Documentation

Open Notebook now includes a comprehensive REST API that provides programmatic access to all functionality. The API includes endpoints for:

- **Notebooks**: Create, read, update, delete notebooks
- **Sources**: Manage research sources (links, files, text)
- **Notes**: Create and manage notes
- **Search**: Full-text and vector search capabilities
- **Models**: Manage AI models and providers
- **Transformations**: Execute content transformations
- **Settings**: Application configuration
- **Context**: Generate context for AI interactions
- **Embedding**: Vectorize content for search

Visit `http://localhost:5055/docs` when the API is running to explore the interactive API documentation.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Usage

Go to the [Usage](docs/USAGE.md) page to learn how to use all features.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Features

- **Multi-Notebook Support**: Organize your research across multiple notebooks effortlessly.
- **Multi-model support**: Open AI, Anthropic, Gemini, Vertex AI, Open Router, X.AI, Groq, Ollama. ([Model Selection Guide](https://github.com/lfnovo/open-notebook/blob/main/docs/models.md))
- **Reasoning Model Support**: Full support for thinking models like DeepSeek-R1, Qwen3, and Magistral with collapsible reasoning sections.
- **Comprehensive REST API**: Full programmatic access to all functionality for building custom integrations.
- **Optional Password Protection**: Secure your public deployments with simple password authentication for both UI and API.
- **Advanced Podcast Generator**: Create professional podcasts with 1-4 speakers using Episode Profiles. Superior flexibility compared to Google Notebook LM's 2-speaker limitation.
- **Broad Content Integration**: Works with links, PDFs, EPUB, Office, TXT, Markdown files, YouTube videos, Audio files, Video files and pasted text.
- **Content Transformation**: Powerful customizable actions to summarize, extract insights, and more.
- **AI-Powered Notes**: Write notes yourself or let the AI assist you in generating insights.
- **Integrated Search Engines**: Built-in full-text and vector search for faster information retrieval.
- **Fine-Grained Context Management**: Choose exactly what to share with the AI to maintain control.
- **Citations**: Ask questions about your documents and get answers with citations.


[![Check out our podcast sample](https://img.youtube.com/vi/D-760MlGwaI/0.jpg)](https://www.youtube.com/watch?v=D-760MlGwaI)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



### 📝 Notebook Page

Three intuitive columns to streamline your work:
1. **Sources**: Manage all research materials.
2. **Notes**: Create or AI-generated notes.
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

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ROADMAP -->
## Roadmap

- [ ] **React Frontend**: Modern React-based frontend to replace Streamlit.
- [ ] **Live Front-End Updates**: Real-time UI updates for a smoother experience.
- [ ] **Async Processing**: Faster UI through asynchronous content processing.
- [ ] **Cross-Notebook Sources and Notes**: Reuse research notes across projects.
- [ ] **Bookmark Integration**: Integrate with your favorite bookmarking app.
- ✅ **Comprehensive REST API**: Full API coverage for all functionality.
- ✅ **Multi-model support**: Open AI, Anthropic, Vertex AI, Open Router, Ollama, etc.
- ✅ **Insight Generation**: New tools for creating insights - [transformations](docs/TRANSFORMATIONS.md)
- ✅ **Advanced Podcast Generator**: Professional multi-speaker podcasts with Episode Profiles and background processing. 
- ✅ **Multiple Chat Sessions**: Juggle different discussions within the same notebook.
- ✅ **Enhanced Citations**: Improved layout and finer control for citations.
- ✅ **Better Embeddings & Summarization**: Smarter ways to distill information.

See the [open issues](https://github.com/lfnovo/open-notebook/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- CONTRIBUTING -->
## Contributing

We would love your contributions! Specifically, we're looking for help with:
- **Front-End Development**: Improve the UI/UX by moving beyond Streamlit.
- **Testing & Bug Fixes**: Help make Open Notebook more robust.
- **Feature Development**: Let’s make the coolest note-taking tool together!

See more at [CONTRIBUTING](CONTRIBUTING.md)

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- LICENSE -->
## License

Open Notebook is MIT licensed. See the [LICENSE](LICENSE) file for details.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTACT -->
## Contact

Luis Novo - [@lfnovo](https://twitter.com/lfnovo)
Join our [Discord server](https://discord.gg/37XJPXfz2w) for help, share workflow ideas, and suggest features.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

This project uses some amazing third-party libraries

* [Podcast Creator](https://github.com/lfnovo/podcast-creator) - Licensed under the MIT License
* [Surreal Commands](https://github.com/lfnovo/surreal-commands) - Licensed under the MIT License
* [Content Core](https://github.com/lfnovo/content-core) - Licensed under the MIT License
* [Docling](https://github.com/docling-project/docling) - Licensed under the MIT License
* [Esperanto](https://github.com/lfnovo/esperanto) - Licensed under the MIT License

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/lfnovo/open-notebook.svg?style=for-the-badge
[contributors-url]: https://github.com/lfnovo/open-notebook/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/lfnovo/open-notebook.svg?style=for-the-badge
[forks-url]: https://github.com/lfnovo/open-notebook/network/members
[stars-shield]: https://img.shields.io/github/stars/lfnovo/open-notebook.svg?style=for-the-badge
[stars-url]: https://github.com/lfnovo/open-notebook/stargazers
[issues-shield]: https://img.shields.io/github/issues/lfnovo/open-notebook.svg?style=for-the-badge
[issues-url]: https://github.com/lfnovo/open-notebook/issues
[license-shield]: https://img.shields.io/github/license/lfnovo/open-notebook.svg?style=for-the-badge
[license-url]: https://github.com/lfnovo/open-notebook/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/lfnovo
[product-screenshot]: images/screenshot.png
[Streamlit]: https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white
[Streamlit-url]: https://streamlit.io/
[Python]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white
[Python-url]: https://www.python.org/
[LangChain]: https://img.shields.io/badge/LangChain-3A3A3A?style=for-the-badge&logo=chainlink&logoColor=white
[LangChain-url]: https://www.langchain.com/
[SurrealDB]: https://img.shields.io/badge/SurrealDB-FF5E00?style=for-the-badge&logo=databricks&logoColor=white
[SurrealDB-url]: https://surrealdb.com/
