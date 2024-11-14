# Configuration and Setup

## Installing Open Notebook

> ⚠️ **Important:** Be sure to edit the `.env` file before running the app.

### 🐳 Docker Setup (recommended)

We recommend using Docker as this will get you all the services installed and configured with no hassle.

Copy the `.env.example` file and name it `docker.env`

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
      - notebook_data:/app/data

volumes:
  surreal_data:
  notebook_data:
```

Take a look at the [Open Notebook Boilerplate](https://github.com/lfnovo/open-notebook-boilerplate) repo with a sample of how to set it up for maximum feature usability. 

### 📦 Installing from Source

If you really want to play with the source code.

```sh
git clone https://github.com/lfnovo/open_notebook.git
cd open_notebook
poetry install
cp .env.example .env
poetry run streamlit run app_home.py
```

Run the app with: 

```sh
poetry run streamlit run app_home.py
```

or the shourcut

```sh
make run
```

## Setting up the providers and models

Several new providers are supported now:

- OpenAI
- Anthropic
- Open Router
- LiteLLM
- Vertex AI
- Gemini
- Ollama
- Groq
- xAI

All providers are installed out of the box. All you need to do is to setup the environment variable configurations (API Keys, etc) for your selected provider and decide which models to use. 

Please refer to the `.env.example` file for instructions on which ENV variables are necessary for each. 

### Create models on the Settings page

Go to the settings page and create your different models. 

| Model Type | Supported Providers |
|------------|-----------|
| Language | OpenAI, Anthropic, Open Router, LiteLLM, Vertex AI, Vertex AI, Anthropic, Gemini, Ollama, xAI, Groq |
| Embedding | OpenAI, Gemini, Vertex AI, Ollama |
| Speech to Text | OpenAI, Groq |
| Text to Speech | OpenAI, ElevenLabs, Gemini |


> 📝 **Notice:** For complete usage of all the features, you need to setup at least 4 models (one of each type). 

After setting up the models, head to the Model Defaults tab to define the default models. There are several defaults to setup. 


| Model Default | Purpose |
|------------|-----------|
| Chat Model | Will be used on all chats |
| Transformation Model | Will be used for summaries, insights, etc |
| Large Context | For content higher then 110k tokens (use Gemini here) |
| Speech to Text | For transcribing text from your audio/video uploads |
| Text to Speech | For generating podcasts  |
| Embedding | For creating vector representation of content |

All model types and defaults are required for now. If you are not sure which to pick, go with OpenAI, the only one that covers all possible model types.

The reason for opting for this route is because different LLMs, will behave better/worse depending on the type of request and type of tools offered. So it makes sense to build a more refined system to decide which model should process which task.

For instance, we can use an Ollama based model, like `gemma2` to do summarization and document query, and use openai/claude for the chat. The whole idea is to allow you to experiment on cost/performance.


## Running the app

After the app is running, you can access it at http://localhost:8080.

The first time you connect, it will check for the database and see if the schema is ready. If not, it will create the database for you. 

Go to the [Usage](USAGE.md) page to learn how to use all features.

## Upgrading Open Notebook

### Running from source

Just run `git pull` on the root project folder and then `poetry install` to update dependencies.

### Running from docker

Just pull the latest image with `docker pull lfnovo/open_notebook:latest` and restart your containers with `docker-compose up -d`