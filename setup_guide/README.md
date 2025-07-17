# Open Notebook - Docker Setup Guide for Beginners

**A step-by-step guide to get Open Notebook running with Docker - no technical experience required!**

## What You'll Get

Open Notebook is a powerful AI-powered research and note-taking tool that:
- Helps you organize research across multiple notebooks
- Lets you chat with your documents using AI
- Supports multiple AI providers (OpenAI, Anthropic, Google, and more)
- Creates AI-generated podcasts from your content
- Works with PDFs, web links, videos, audio files, and more

## Prerequisites

Before we start, you'll need:
- A computer running Windows, macOS, or Linux
- An internet connection
- At least one AI provider API key (see section below)

## Step 1: Install Docker Desktop

Docker Desktop is the software that will run Open Notebook on your computer.

### For Windows:
1. Go to https://www.docker.com/products/docker-desktop/
2. Click "Download for Windows"
3. Run the downloaded installer
4. Follow the installation wizard
5. Restart your computer when prompted

### For macOS:
1. Go to https://www.docker.com/products/docker-desktop/
2. Click "Download for Mac"
3. Choose your Mac type (Intel or Apple Silicon)
4. Open the downloaded .dmg file
5. Drag Docker to your Applications folder
6. Open Docker from Applications

### For Linux (Ubuntu/Debian):
1. Open Terminal
2. Run these commands one by one:
```bash
sudo apt update
sudo apt install docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```
3. Log out and log back in

## Step 2: Get Your OpenAI API Key

Open Notebook uses OpenAI's powerful AI models. With just one API key, you'll have access to everything you need:
- **Text generation** for chat and notes
- **Embeddings** for search functionality  
- **Text-to-speech** for podcast generation
- **Speech-to-text** for audio transcription

### How to Get Your OpenAI API Key

1. Go to https://platform.openai.com/
2. Create an account or sign in
3. Click on **"API Keys"** in the left sidebar
4. Click **"Create new secret key"**
5. Give your key a name (e.g., "Open Notebook")
6. Copy the key that appears (it starts with "sk-")
7. **Save this key somewhere safe** - you won't be able to see it again!

### Add Credits to Your Account

**Important**: OpenAI requires you to add credits before you can use the API.

1. In the OpenAI platform, click **"Billing"** in the sidebar
2. Click **"Add payment details"**
3. Add at least **$5 in credits** (this will last a long time for personal use)
4. You can set up usage limits to control spending

## Step 3: Create Your Configuration Files

### Create the docker-compose.yml file

1. Create a new folder on your computer called `open-notebook`
2. Open a text editor (Notepad on Windows, TextEdit on Mac, or any text editor)
3. Copy and paste this content -- or download it from [here](https://github.com/lfnovo/open-notebook/blob/main/docker-compose.yml):

```yaml
services:
  open_notebook:
    image: lfnovo/open_notebook:latest-single
    ports:
      - "8080:8502"
    env_file:
      - ./docker.env
    pull_policy: always
    volumes:
      - ./notebook_data:/app/data
      - ./surreal_data:/app/surreal_data
    restart: always
```

4. Save this file as `docker-compose.yml` in your `open-notebook` folder

### Create the docker.env file

1. In the same `open-notebook` folder, create a new file
2. Copy and paste this content, replacing `YOUR_OPENAI_API_KEY_HERE` with your actual API key -- or download it from [here](https://github.com/lfnovo/open-notebook/blob/main/.env.example) - be sure to rename it to `docker.env`:

```env
# REQUIRED: Your OpenAI API key
OPENAI_API_KEY=YOUR_OPENAI_API_KEY_HERE

# Database settings (don't change these)
SURREAL_ADDRESS=localhost
SURREAL_PORT=8000
SURREAL_USER=root
SURREAL_PASS=root
SURREAL_NAMESPACE=open_notebook
SURREAL_DATABASE=production
```

3. **Important**: Replace `YOUR_OPENAI_API_KEY_HERE` with your actual API key from Step 2
4. Save this file as `docker.env` in your `open-notebook` folder

## Step 4: Start Open Notebook

### Windows:
1. Open Command Prompt
2. Navigate to your open-notebook folder: `cd C:\path\to\your\open-notebook`
3. Run: `docker-compose up -d`

### macOS/Linux:
1. Open Terminal
2. Navigate to your open-notebook folder: `cd /path/to/your/open-notebook`
3. Run: `docker-compose up -d`

### What happens next:
- Docker will download the necessary files (this might take a few minutes the first time)
- Two services will start: the database and Open Notebook
- You'll see messages indicating the services are starting

### Important

- Make sure that Docker Desktop is running before starting Open Notebook.
- Make sure both the `docker-compose.yml` and `docker.env` files are in this folder where you run the `docker-compose up -d` command.

## Step 5: Access Open Notebook

1. Open your web browser
2. Go to: http://localhost:8502
3. You should see the Open Notebook interface!

## Step 6: Configure Your AI Models

Before creating your first notebook, you need to set up which AI models to use for different tasks.

### Navigate to Models Settings

1. Click on **"⚙️ Settings"** in the sidebar
2. Click on **"🤖 Models"** tab

### Set Up Your Models

You'll need to configure models for different purposes. Here are the recommended OpenAI models for each category:

#### 1. **Language Models** (For conversations and general AI assistance)
- **Recommended**: `gpt-4o-mini` (fast and cost-effective)
- **Alternative**: `gpt-4o` (more powerful but costs more)

#### 2. **Embedding Model** (For search and finding similar content)
- **Recommended**: `text-embedding-3-small` (best balance)
- **Alternative**: `text-embedding-3-large` (better quality, costs more)
- **Note**: This is required for the search feature to work

#### 3. **Text-To-Speech Model** (For processing your documents)
- **Recommended**: `gpt-4o-mini-tts` (handles long documents well)
- **Alternative**: `tts-1` (cheaper, less quality)

#### 4. **Speech-to-Text Model** (For generating podcasts)
- **Recommended**: `whisper-1` (best quality for creative content)

### How to Configure Each Model

1. For each model category, click the dropdown menu
2. Select your chosen model from the list
3. Click **"Save"** after configuring all models
4. You should see a success message

### Tips for Model Selection

- **Start with the recommended models** - they provide the best balance of quality and cost
- **You can change models anytime** - experiment to find what works best
- **Check your OpenAI usage** - monitor costs at https://platform.openai.com/usage
- **All these models use your OpenAI API key** - no additional setup needed

## Step 7: Create Your First Notebook

1. Click "Create New Notebook"
2. Give it a name (e.g., "My Research")
3. Add a description
4. Click "Create"

## Step 8: Add Your First Source

1. In your new notebook, click "Add Source"
2. Choose from:
   - **Link**: Paste any web URL
   - **File**: Upload PDFs, documents, audio, or video files
   - **Text**: Paste text directly
3. Click "Add Source"
4. Wait for processing to complete

## Step 9: Start Using Open Notebook

Now you can:
- **Chat with your content**: Use the chat panel to ask questions about your sources
- **Create notes**: Write or generate AI-powered notes
- **Generate podcasts**: Create multi-speaker podcasts from your content
- **Search**: Find information across all your sources
- **Add more sources**: Keep building your knowledge base

## Troubleshooting

### Port already in use
If you get an error about port 8502 being in use:
1. Stop the current container: `docker-compose down`
2. Wait a few seconds
3. Start again: `docker-compose up -d`

### Can't access the interface
- Make sure Docker Desktop is running
- Check that both containers are running: `docker-compose ps`
- Try restarting: `docker-compose restart`

### API key errors
- Double-check your API keys in the `docker.env` file
- Make sure you have credits in your AI provider account
- Verify the keys don't have extra spaces or characters

### General issues
1. Stop everything: `docker-compose down`
2. Remove old containers: `docker-compose down -v`
3. Start fresh: `docker-compose up -d`

## Stopping Open Notebook

To stop Open Notebook:
```bash
docker-compose down
```

To start it again:
```bash
docker-compose up -d
```

## Getting Help

- **Discord**: Join the Open Notebook community at https://discord.gg/37XJPXfz2w
- **GitHub Issues**: Report bugs at https://github.com/lfnovo/open-notebook/issues
- **Documentation**: Visit https://www.open-notebook.ai for more features and guides

## Next Steps

Once you're comfortable with the basics:
- Try the transformation features to extract insights
- Create multi-speaker podcasts from your research
- Experiment with different OpenAI models for various tasks
- Explore the search functionality to find information quickly

## Ready for More? Check Out the Advanced Guide!

Now that you have Open Notebook running with OpenAI, you might want to explore more AI providers and advanced features. Check out our [Advanced Docker Setup Guide](DOCKER_SETUP_ADVANCED.md) to learn about:

- **OpenRouter**: Access to 100+ models from different providers (Claude, Gemini, Llama, etc.)
- **Ollama**: Run AI models locally on your computer for complete privacy
- **Additional providers**: Anthropic, Google, Groq, and more
- **Advanced configurations**: Custom model settings and optimizations

Welcome to Open Notebook! 🚀