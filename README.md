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
>
> ⚠️ **API Changes**: As we optimize and enhance the project, some APIs and interfaces might change. We'll do our best to document these changes and minimize disruption.
>
> 🙏 **We Need Your Feedback**: Please try out Open Notebook and let us know what you think! Submit issues, feature requests, or just share your experience through:
> - GitHub Issues
> - Discussions
> - Pull Requests
>
> Together, we can make it even better! 


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

To run the source code locally and experiment with the code, you just need to run:

```bash
uv sync
docker compose --profile db_only up
uv run streamlit run app_home.py
```

If you don't want to mess around with the code and just want to run it as a docker image:

```bash
docker compose --profile multi up
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Usage

Go to the [Usage](docs/USAGE.md) page to learn how to use all features.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Features

- **Multi-Notebook Support**: Organize your research across multiple notebooks effortlessly.
- **Multi-model support**: Open AI, Anthropic, Gemini, Vertex AI, Open Router, X.AI, Groq,Ollama.
- **Podcast Generator**: Automatically convert your notes into a podcast format.
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

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ROADMAP -->
## Roadmap

- [ ] **Live Front-End Updates**: Real-time UI updates for a smoother experience.
- [ ] **Async Processing**: Faster UI through asynchronous content processing.
- [ ] **Cross-Notebook Sources and Notes**: Reuse research notes across projects.
- [ ] **Bookmark Integration**: Integrate with your favorite bookmarking app.
- ✅ **Multi-model support**: Open AI, Anthropic, Vertex AI, Open Router, Ollama, etc.
- ✅ **Insight Generation**: New tools for creating insights - [transformations](docs/TRANSFORMATIONS.md)
- ✅ **Podcast Generator**: Automatically convert your notes into a podcast format. 
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

* [Podcastfy](https://github.com/souzatharsis/podcastfy) - Licensed under the Apache License 2.0
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
