# Ollama MCP Server for VS Code Agent

This guide shows how to use Ollama models (**DeepSeek**, **Mistral**, and **CodeLlama**) with VS Code's agent functionality. **DeepSeek Coder** is the primary model for code-related tasks.

## Setup Steps

### 1. Install Ollama

Download and install from [ollama.ai](https://ollama.ai)

### 2. Pull the Models

Run these commands to download the models:

```powershell
ollama pull deepseek-coder
ollama pull mistral
ollama pull codellama
```

### 3. Verify Models Installation

```powershell
ollama list
```

You should see:
- `deepseek-coder:latest` - Specialized for code generation (PRIMARY MODEL)
- `mistral:latest` - Fast, general-purpose model
- `codellama:latest` - Alternative code generation model

### 4. Start Ollama Server

Before using the agent, start the Ollama service:

```powershell
ollama serve
```

This runs Ollama on `http://localhost:11434`

### 5. VS Code Configuration

The MCP server is already configured in `.vscode/settings.json`:

```json
{
    "modelContextProtocol.servers": {
        "ollama": {
            "command": "python",
            "args": ["${workspaceFolder}/ollama_mcp_server.py"],
            "disabled": false
        }
    }
}
```

### 6. Using the Agent

Once Ollama server is running, restart VS Code and the Ollama MCP server will be available.

## Agent Tools

Your VS Code agent now has access to:

### `ask_ollama`
Ask a question using your choice of model
```
@agent: What is the best way to implement caching in Python?
```
Models available: `deepseek-coder` (code tasks), `mistral` (general), `codellama` (code generation)

### `generate_code`
Generate code using **DeepSeek Coder** (specialized for code)
```
@agent: Generate Python code for a REST API endpoint that handles POST requests
```

### `chat_ollama`
Have a multi-turn conversation with full context
```
@agent: [Conversation with history]
```

### `list_models`
See what models are available
```
@agent: What models are available?
```

## Models Configuration

- **Primary Model**: DeepSeek Coder (excellent for code generation and analysis)
- **General Model**: Mistral (fast, great for general tasks)
- **Fallback**: DeepSeek Coder (automatic fallback if specified model unavailable)
- **Alternative Code Model**: CodeLlama (if you prefer this for code generation)

## Using DeepSeek Coder

DeepSeek Coder is now the primary model for code-related tasks. It provides excellent code generation, analysis, and debugging capabilities.

### Example Usage

**For code generation:**
```
@agent: Generate a Python function to validate email addresses
```

**For code analysis:**
```
@agent: Using deepseek-coder model, analyze this code for performance issues: [paste code]
```

**For specific model selection:**
```
@agent ask_ollama model=deepseek-coder: How do I implement authentication in Flask?
```

### When to Use Each Model

| Model | Use Case | Speed |
|-------|----------|-------|
| **deepseek-coder** | Code generation, debugging, analysis | Medium |
| **mistral** | General questions, explanations | Fast |
| **codellama** | Alternative for specialized code tasks | Medium-Slow |

## Troubleshooting

### Issue: "Cannot connect to Ollama"
**Solution**: 
1. Make sure Ollama is running: `ollama serve`
2. Verify it's accessible: `curl http://localhost:11434/api/tags`

### Issue: Model takes too long to respond
**Solution**: 
- DeepSeek Coder can be slower for large prompts (but provides better quality)
- Try Mistral for faster responses on general questions
- Check system resources (CPU/RAM)
- DeepSeek requires more VRAM than Mistral

### Issue: "ollama: command not found"
**Solution**:
- Ensure Ollama is installed and added to your PATH
- Restart PowerShell after installing Ollama
- Try the full path: `C:\Program Files\Ollama\ollama.exe serve`

### Issue: DeepSeek model not pulling
**Solution**:
```powershell
ollama pull deepseek-coder
# Or if you want the larger model:
ollama pull deepseek-coder:7b
```

### Issue: Agent doesn't see the Ollama tools
**Solution**:
1. Restart VS Code
2. Check that Ollama server is running
3. Check Output → "MCP" for any connection errors

## Advanced: Using Other Models

To add more models, edit `ollama_mcp_server.py`:

```python
DEFAULT_MODELS = ["mistral", "codellama", "neural-chat"]  # Add more models
```

Then pull them:
```powershell
ollama pull neural-chat
```

## Performance Tips

1. **Keep Ollama running** - Start `ollama serve` before using VS Code
2. **Use Mistral for quick responses** - Faster than DeepSeek for general questions
3. **Use DeepSeek Coder for coding tasks** - Optimized for code generation and analysis
4. **Monitor system resources** - Models need 8GB+ RAM for best performance
5. **GPU Acceleration** - Ollama will automatically use GPU if available (NVIDIA/Apple)
6. **Model Preloading** - First request to a model is slower (it loads into memory); subsequent requests are faster

## Files

- `ollama_mcp_server.py` - MCP server that bridges VS Code and Ollama
- `.vscode/settings.json` - Configuration for the MCP server
