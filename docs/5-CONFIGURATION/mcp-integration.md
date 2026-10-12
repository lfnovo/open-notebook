# Model Context Protocol (MCP) Integration

Open Notebook can be seamlessly integrated into your AI workflows using the **Model Context Protocol (MCP)**, enabling direct access to your notebooks, sources, and chat functionality from AI assistants like Claude Desktop and VS Code extensions.

## What is MCP?

The [Model Context Protocol](https://modelcontextprotocol.io) is an open standard that allows AI applications to securely connect to external data sources and tools. With the Open Notebook MCP server, you can:

- 📚 **Access your notebooks** directly from Claude Desktop or VS Code
- 🔍 **Search your research content** without leaving your AI assistant
- 💬 **Create and manage chat sessions** with your research as context
- 📝 **Generate notes** and insights on-the-fly
- 🤖 **Automate workflows** using the full Open Notebook API

## Quick Setup

### For Claude Desktop

1. **Install the MCP server** (automatically from PyPI):

   ```bash
   # No manual installation needed! Claude Desktop will use uvx to run it automatically
   ```

2. **Configure Claude Desktop**:

   **macOS**: Edit `~/Library/Application Support/Claude/claude_desktop_config.json`

   ```json
   {
     "mcpServers": {
       "open-notebook": {
         "command": "uvx",
         "args": ["open-notebook-mcp"],
         "env": {
           "OPEN_NOTEBOOK_URL": "http://localhost:5055",
           "OPEN_NOTEBOOK_PASSWORD": "your_password_here"
         }
       }
     }
   }
   ```

   **Windows**: Edit `%APPDATA%\Claude\claude_desktop_config.json`

   ```json
   {
     "mcpServers": {
       "open-notebook": {
         "command": "uvx",
         "args": ["open-notebook-mcp"],
         "env": {
           "OPEN_NOTEBOOK_URL": "http://localhost:5055",
           "OPEN_NOTEBOOK_PASSWORD": "your_password_here"
         }
       }
     }
   }
   ```

3. **Restart Claude Desktop** and start using your notebooks in conversations!

### For VS Code (Cline and other MCP-compatible extensions)

Add to your VS Code settings or `.vscode/mcp.json`:

```json
{
  "servers": {
    "open-notebook": {
      "command": "uvx",
      "args": ["open-notebook-mcp"],
      "env": {
        "OPEN_NOTEBOOK_URL": "http://localhost:5055",
        "OPEN_NOTEBOOK_PASSWORD": "your_password_here"
      }
    }
  }
}
```

## Configuration

- **OPEN_NOTEBOOK_URL**: URL to your Open Notebook API (default: `http://localhost:5055`)
- **OPEN_NOTEBOOK_PASSWORD**: Optional - only needed if you've enabled password protection

### For Remote Servers

If your Open Notebook instance is running on a remote server, update the URL accordingly:

```json
"OPEN_NOTEBOOK_URL": "http://192.168.1.100:5055"
```

## What You Can Do

Once connected, you can ask Claude or your AI assistant to:

- _"Search my research notebooks for information about [topic]"_
- _"Create a new note summarizing the key points from our conversation"_
- _"List all my notebooks"_
- _"Start a chat session about [specific source or topic]"_
- _"What sources do I have in my [notebook name] notebook?"_
- _"Add this PDF to my research notebook"_
- _"Show me all notes in [notebook name]"_

The MCP server provides full access to Open Notebook's capabilities, allowing you to manage your research seamlessly from within your AI assistant.

## Available Tools

The Open Notebook MCP server exposes these capabilities:

### Notebooks

- List notebooks
- Get notebook details
- Create new notebooks
- Update notebook information
- Delete notebooks

### Sources

- List sources in a notebook
- Get source details
- Add new sources (links, files, text)
- Update source metadata
- Delete sources

### Notes

- List notes in a notebook
- Get note details
- Create new notes
- Update notes
- Delete notes

### Chat

- Create chat sessions
- Send messages to chat sessions
- Get chat history
- List chat sessions

### Search

- Vector search across content
- Text search across content
- Filter by notebook

### Models

- List configured AI models
- Get model details
- Create model configurations
- Update model settings

### Settings

- Get application settings
- Update settings

## MCP Server Repository

The Open Notebook MCP server is developed and maintained by the Epochal team:

**🔗 GitHub**: [Epochal-dev/open-notebook-mcp](https://github.com/Epochal-dev/open-notebook-mcp)

Contributions, issues, and feature requests are welcome!

## Finding the Server

The Open Notebook MCP server is published to the official MCP Registry:

- **Registry**: Search for "open-notebook" at [registry.modelcontextprotocol.io](https://registry.modelcontextprotocol.io)
- **PyPI**: [pypi.org/project/open-notebook-mcp](https://pypi.org/project/open-notebook-mcp)
- **GitHub**: [Epochal-dev/open-notebook-mcp](https://github.com/Epochal-dev/open-notebook-mcp)

## Troubleshooting

### Connection Errors

1. Verify the `OPEN_NOTEBOOK_URL` is correct and accessible
2. If using password protection, ensure `OPEN_NOTEBOOK_PASSWORD` is set correctly
3. For remote servers, make sure port 5055 is accessible from your machine
4. Check firewall settings if connecting to a remote server

## Using with Other MCP Clients

The Open Notebook MCP server follows the standard MCP protocol and can be used with any MCP-compatible client. Check your client's documentation for configuration details.

## External MCP retriever (Ask context)

The sections above make Open Notebook an MCP **server**: other assistants can read your notebooks. This section is the other direction. Ask can also be an MCP **client**, and pull extra context from a connector you already run.

Ask only searches what is inside the notebook. A connector you already use elsewhere (docs, tickets, a private corpus, another MCP server) stays invisible unless you copy it in as sources. Setting one URL lets Ask call that connector too, without a new provider or a notebook import.

The feature is off until `OPEN_NOTEBOOK_EXTERNAL_MCP_URL` is set. Set it on the API process (Docker: the `open_notebook` service `environment:` block, then `docker compose up -d`).

```bash
# Streamable HTTP endpoint of the MCP server. Required to enable the feature.
OPEN_NOTEBOOK_EXTERNAL_MCP_URL=https://mcp.example.com/mcp

# Optional bearer token, sent as Authorization. Leave unset for an open server.
# If TOKEN is unset, the same token is read from TOKEN_FILE instead.
OPEN_NOTEBOOK_EXTERNAL_MCP_TOKEN=
OPEN_NOTEBOOK_EXTERNAL_MCP_TOKEN_FILE=

# Tool the client calls. Default: search
# Called with {"query": "<ask search term>", "<LIMIT_ARG>": <LIMIT>}.
OPEN_NOTEBOOK_EXTERNAL_MCP_SEARCH_TOOL=search

# How many hits to request, and the argument name the tool actually uses.
# Defaults: 5 and limit. Set LIMIT_ARG when the tool names that integer something else.
OPEN_NOTEBOOK_EXTERNAL_MCP_LIMIT=5
OPEN_NOTEBOOK_EXTERNAL_MCP_LIMIT_ARG=limit

# Seconds for the HTTP connection. Default: 30
OPEN_NOTEBOOK_EXTERNAL_MCP_TIMEOUT=30
```

What happens on each Ask search term:

1. Local vector search runs as before.
2. If the URL is set, Open Notebook opens a Streamable HTTP MCP session (`initialize`, then `tools/call`) and calls the named tool.
3. Snippets are appended to the local hits before the answer model sees them.
4. If the connector is down, times out, or returns an error, Ask continues with local hits only. The failure is a warning in the API log, not an error for the user.

The connector is responsible for ranking, access control and freshness. Open Notebook does not re-score the snippets.

Result shape the client understands, in order:

- `structuredContent.results` (also `items` or `documents`): a list of objects with `content` or `text`, and optionally `id`, `title`, and `score`, `similarity`, `relevance_score`, or a numeric `confidence`.
- The same object when the tool returns it as a JSON text block instead of `structuredContent`. An empty list stays empty. It is not pasted into the prompt as raw JSON.
- Otherwise, text content blocks from the tool are joined into one snippet.

Ids may be strings or numbers. They are prefixed with `external:` so they cannot collide with `source:`, `note:` or `insight:` records.

Those citations are labels in the answer. They are not notebook records, and the UI cannot open them.

The search term is sent to the connector. Leave the URL unset if that term must not leave the machine.

This path is Ask only. Notebook chat and source chat do not call it.

## Learn More

- [Model Context Protocol Documentation](https://modelcontextprotocol.io)
