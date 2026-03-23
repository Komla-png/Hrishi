# Ollama MCP Server Setup for VS Code Agent

This guide explains how to use Ollama as a local AI agent within VS Code for your Academy Dashboard project.

## Prerequisites

1. **Ollama installed**: Download from [ollama.ai](https://ollama.ai)
2. **A local model**: Run `ollama pull llama2` (or `mistral`, `neural-chat`, etc.)
3. **VS Code with Copilot**: Required for agent functionality

## Quick Start

### 1. Start Ollama Server

```powershell
ollama serve
```

This runs Ollama on `http://localhost:11434`

Available models:
- `llama2` - General purpose, good for code/docs
- `mistral` - Faster, lighter model
- `neural-chat` - Optimized for conversations
- `codellama` - Specialized for code generation

### 2. Verify Setup

```powershell
ollama list  # See installed models
ollama run llama2  # Test a model
```

### 3. VS Code Configuration

The `.vscode/settings.json` is already configured. When you restart VS Code:

1. Open the Agent panel (Copilot > Agent)
2. Look for "Academy Dashboard Agent"
3. Start asking questions

### 4. Using the Agent

In VS Code, use the agent to:

```
@ask_ollama: How do I fix the coach duplicate removal?
@chat_ollama: Help me write a new analytics endpoint
@list_models: Show available Ollama models
```

## Python Script Usage

You can also use the MCP server directly in your app:

```python
from ollama_mcp_server import agent

# Ask a question
response = agent.generate("Explain the coaches database schema")
print(response)

# Chat with history
messages = [
    {"role": "user", "content": "What is a center?"},
    {"role": "assistant", "content": "..."},
    {"role": "user", "content": "How is it related to coaches?"}
]
response = agent.chat(messages)
```

## Troubleshooting

### "Cannot connect to Ollama"
- Ensure `ollama serve` is running
- Check port 11434 is not blocked
- Verify with: `curl http://localhost:11434/api/tags`

### Agent not appearing
- Restart VS Code
- Check `.vscode/settings.json` syntax
- Ensure `.agent.md` is in workspace root

### Slow responses
- Using a lightweight model helps (mistral)
- Increase Ollama's system resources
- Reduce model context window if needed

## Advanced: Custom Models

1. Download a model:
   ```powershell
   ollama pull mistral
   ollama pull neural-chat
   ollama pull codellama
   ```

2. Update `ollama_mcp_server.py` DEFAULT_MODEL:
   ```python
   DEFAULT_MODEL = "mistral"
   ```

## File Structure

```
.vscode/
  ├── settings.json          # MCP server configuration
  └── tasks.json             # Existing tasks

.agent.md                     # Agent personality & expertise
ollama_mcp_server.py         # MCP server implementation
OLLAMA_SETUP.md              # This file
```

## Performance Tips

- **llama2**: Good balance (7B params, ~5GB)
- **mistral**: Faster, smaller (7B params, ~3.5GB)
- **neural-chat**: Best for chatting (7B params)
- **codellama**: Best for code, slower (7B-34B params)

Use `mistral` for quick feedback, `llama2` for detailed analysis.

## API Reference

See `ollama_mcp_server.py` for available tools:
- `ask_ollama(prompt, model)` - Single question
- `chat_ollama(messages, model)` - Conversation
- `list_models()` - Show available models

## Limitations

- Local only (no internet required)
- Response quality depends on model size
- First load of a model is slow (~1-2 min)
- Model runs on CPU by default (GPU optional)

## More Information

- [Ollama Documentation](https://github.com/ollama/ollama)
- [MCP Protocol](https://modelcontextprotocol.io)
- [VS Code Agents](https://code.visualstudio.com/docs/copilot/agents)
