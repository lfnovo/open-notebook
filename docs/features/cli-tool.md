# 🖥️ ACM Scholar CLI

A powerful command-line tool for academic research, powered by Gemini API.

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📚 **Paper Search** | Search academic papers via OpenAlex |
| 📥 **PDF Download** | Download papers from multiple sources |
| 🤖 **AI Chat** | Interactive Q&A with Gemini |
| 📊 **Data Export** | Export QA pairs for model fine-tuning |
| 📈 **Analytics** | Track your research activity |

## 🚀 Quick Install

```bash
# Install via pip
pip install acm-scholar-cli

# Or install from source
git clone https://github.com/hongping-zh/acm-scholar-cli.git
cd acm-scholar-cli
pip install -e .
```

## ⚙️ Configuration

Create config file at `~/.config/acm-scholar/config.yaml`:

```yaml
openalex:
  email: your-email@example.com

llm:
  provider: gemini
  api_key: YOUR_GEMINI_API_KEY
  model: gemini-2.0-flash

download:
  directory: ~/acm-papers/
```

## 📖 Usage

### Search Papers
```bash
# Search for papers
acm search "transformer attention mechanism"

# Search with filters
acm search "deep learning" --year 2023 --limit 10
```

### Download Papers
```bash
# Download by DOI
acm download 10.1145/1234567.1234568

# Batch download from search results
acm search "neural network" --download
```

### AI Chat
```bash
# Start interactive chat
acm chat

# Ask a question about a paper
acm chat ask "What is the main contribution of this paper?"

# Chat with specific paper loaded
acm chat --paper ./paper.pdf
```

### Data Export
```bash
# Export QA pairs for fine-tuning
acm data export --format jsonl --output training_data.jsonl

# View statistics
acm data stats
```

## 🏆 Built for Gemini API Competition

This CLI tool demonstrates:
- **Data Moat Strategy**: Automatic QA pair collection
- **OpenAlex Integration**: Academic knowledge graph search
- **Gemini API**: Multimodal AI capabilities

## 📊 Example Output

```
$ acm search "transformer"

🔍 Found 5 papers:

[1] Attention Is All You Need (2017)
    Authors: Vaswani, Shazeer, Parmar...
    Citations: 98,234
    DOI: 10.48550/arXiv.1706.03762

[2] BERT: Pre-training of Deep Bidirectional...
    Authors: Devlin, Chang, Lee...
    Citations: 76,543
    ...
```

## 🔗 Links

- **Source Code**: [GitHub](https://github.com/hongping-zh/acm-scholar-cli)
- **PyPI**: [acm-scholar-cli](https://pypi.org/project/acm-scholar-cli/)
- **Documentation**: This page

---

*Part of the Open Notebook ecosystem • Powered by Gemini API*
