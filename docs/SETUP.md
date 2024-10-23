# Configuration and Setup

## Installing Open Notebook


### 📦 Installing from Source

Quickly get started by cloning and installing the dependencies.

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

> ⚠️ **Important:** Be sure to edit the `.env` file before running the app.


### 🐳 Docker Setup

Alternatively, you can use Docker for easy setup.

Copy the `.env.example` file and name it `docker.env`

```sh
docker run -d \
  --name open_notebook \
  -p 8080:8502 \
  -v $(pwd)/docker.env:/app/.env \
  lfnovo/open_notebook:latest
```

You can pass the environment variables manually if you want:

```sh
docker run -d \
  --name open_notebook \
  -p 8080:8502 \
  -e OPENAI_API_KEY=API_KEY \
  -e DEFAULT_MODEL="gpt-4o-mini" \
  -e SURREAL_ADDRESS="localhost" \
  -e SURREAL_PORT=8000 \
  -e SURREAL_USER="root" \
  -e SURREAL_PASS="root" \
  -e SURREAL_NAMESPACE="open_notebook" \
  -e SURREAL_DATABASE="staging" \
  lfnovo/open_notebook:latest
```

If you need to run Surreal DB on docker as well, it's easier to just use docker-compose, like this:

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

or with the environment variables:

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
    environment:
        - OPENAI_API_KEY=API_KEY
        - DEFAULT_MODEL=gpt-4o-mini
        - SURREAL_ADDRESSsurrealdb
        - SURREAL_PORT=8000
        - SURREAL_USER=root
        - SURREAL_PASS=root
        - SURREAL_NAMESPACE=open_notebook
        - SURREAL_DATABASE=staging
    depends_on:
        - surrealdb
    pull_policy: always
```


## Setting up the providers

Several new providers are supported now:

- OpenAI
- Anthropic
- Open Router
- LiteLLM
- Vertex AI
- Ollama

All providers are installed out of the box. All you need to do is to setup the environment variable configurations (API Keys, etc) for your selected provider and decide which models to use. 

Please refer to the `.env.example` file for instructions on which ENV variables are necessary for each. 

### Use provider-modelname convention

You should prepend the provider name to the model_name when setting up your env variables, examples: 

- openai/gpt-4o-mini
- anthropic/claude-3-5-sonnet-20240620
- ollama/gemma2
- openrouter/nvidia/llama-3.1-nemotron-70b-instruct
- vertexai/gemini-1.5-flash-001

__There will be a UI configuration for models in the coming days.__

## Setup 2 models for more flexibility

There are 2 configurations for models at this point: 

```
DEFAULT_MODEL="openai/gpt-4o-mini"
SUMMARIZATION_MODEL="openrouter/nvidia/llama-3.1-nemotron-70b-instruct"
```

- **DEFAULT_MODEL** is used by the chat tool
- **SUMMARIZATION_MODEL (optional)** is used on the content summarization

The reason for opting for this route is because different LLMs, will behave better/worse depending on the type of request and type of tools offered. So it makes sense to build a more refined system to decide which model should process which task.

For instance, we can use an Ollama based model, like `gemma2` to do summarization and document query, and use openai/claude for the chat. The whole idea is to allow you to experiment on cost/performance.


## Running the app

After the app is running, you can access it at http://localhost:8080.

The first time you connect, it will check for the database and see if the schema is ready. If not, it will create the database for you. 

Go to the [Usage](USAGE.md) page to learn how to use all features.
