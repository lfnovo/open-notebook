# ACM Scholar Agent - User Testing Guide

Welcome to the ACM Scholar Agent testing! This guide will help you get started with searching and adding academic papers to your Open Notebook.

## 🚀 Quick Start

### What You Can Do (No API Key Required!)

- **Search ACM Papers** - Find open access papers from ACM Digital Library
- **Add Papers to Notebook** - One-click download and import from arXiv and other trusted sources
- **View Paper Content** - See extracted text from PDFs

### For Full Experience (Optional)

To chat with your papers using AI, you'll need one of these:
- **DeepSeek API Key** (Recommended, affordable)
- **OpenAI API Key**
- **Ollama** (Free, runs locally)

---

## 📦 Installation

### Prerequisites

- Python 3.10+
- Node.js 18+
- SurrealDB

### 1. Clone the Repository

```bash
git clone https://github.com/hongping-zh/open-notebook.git
cd open-notebook
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Mac/Linux)
source .venv/bin/activate

# Install dependencies
pip install -e .
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

### 4. Database Setup

Start SurrealDB:
```bash
surreal start --user root --pass root file:data/surreal
```

### 5. Environment Configuration

Create `.env` file in the project root:

```env
API_URL=http://localhost:5055
INTERNAL_API_URL=http://localhost:5055
SURREAL_URL="ws://127.0.0.1:8000/rpc"
SURREAL_USER="root"
SURREAL_PASSWORD="root"
SURREAL_NAMESPACE="open_notebook"
SURREAL_DATABASE="staging"
```

### 6. Start the Application

**Terminal 1 - Backend:**
```bash
python run_api.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Open browser:** http://localhost:3000

---

## 🔍 Testing the ACM Agent

### Step 1: Create a Notebook

1. Click **"+ New Notebook"**
2. Give it a name (e.g., "AI Research")

### Step 2: Search for Papers

1. In your notebook, click **"+ Add"** button
2. Select **"Research Papers"** from the dropdown
3. Enter a search query (e.g., "Large Language Models", "Reinforcement Learning")
4. Click **Search**

### Step 3: Add a Paper

1. Browse the search results
2. Click **"+ Add"** on any paper you want
3. The paper will be downloaded and processed automatically

### Step 4: View Your Paper

- The paper appears in your Sources list
- Click to view extracted content
- Status shows: Processing → Embedded (ready for chat)

---

## 💬 Chat with Your Papers (Optional)

To enable AI chat, configure a language model:

### Option A: DeepSeek (Recommended)

1. Get API key from https://platform.deepseek.com/
2. Go to **Settings** → **Models** in Open Notebook
3. Add new model:
   - Provider: `deepseek`
   - Name: `deepseek-chat`
   - API Key: Your key
4. Set as default chat model

### Option B: Ollama (Free, Local)

1. Install Ollama: https://ollama.ai/
2. Pull a model: `ollama pull llama2`
3. Configure in Open Notebook Settings

---

## 🧪 Test Scenarios

### Scenario 1: Basic Search
- Query: "neural network optimization"
- Expected: 3-5 papers with arXiv links

### Scenario 2: Specific Topic
- Query: "transformer attention mechanism"
- Expected: Papers about attention in transformers

### Scenario 3: Add and Process
- Add any paper from search results
- Wait for processing (usually < 1 minute)
- Verify content is extracted

### Scenario 4: Chat (if configured)
- Ask: "What is the main contribution of this paper?"
- Expected: AI response based on paper content

---

## ❓ Troubleshooting

### No Search Results?
- Try broader search terms
- ACM Agent only returns papers with accessible PDFs (arXiv, etc.)

### Paper Stuck in "Processing"?
- Check backend logs for errors
- Ensure SurrealDB is running

### Chat Not Working?
- Verify LLM model is configured
- Check API key is valid
- Look at backend logs for errors

---

## 📝 Feedback

We'd love to hear your feedback! Please report:
- Bugs or errors
- Feature requests
- User experience issues

Contact: [Your contact info or GitHub Issues]

---

## 🔗 Links

- **Repository**: https://github.com/hongping-zh/open-notebook
- **Original Project**: https://github.com/lfnovo/open-notebook
- **OpenAlex API**: https://openalex.org/

---

**Happy researching!** 📚
