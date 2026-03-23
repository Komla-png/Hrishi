#!/usr/bin/env python3
"""
Ollama MCP Server for VS Code Integration
Allows VS Code agents to use local Ollama models via Model Context Protocol
"""

import json
import logging
import sys
from typing import Any
import requests
import asyncio

# Configure logging to stderr to avoid interfering with MCP communication
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODELS = ["deepseek-coder", "mistral", "codellama"]  # Primary models: deepseek for code, mistral for general
FALLBACK_MODEL = "deepseek-coder"  # Use deepseek-coder if specified model unavailable

class OllamaAgent:
    """Wrapper for Ollama API integration"""
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
        self.available_models = []
        self._check_connection()
    
    def _check_connection(self):
        """Verify Ollama is running"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.available_models = [model['name'] for model in data.get('models', [])]
                logger.info(f"Ollama connected. Available models: {self.available_models}")
            else:
                logger.warning("Ollama returned non-200 status")
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Ollama at {self.base_url}")
            logger.info("Make sure Ollama is running: ollama serve")
            self.available_models = []
    
    def generate(self, prompt: str, model: str = None, stream: bool = False) -> str:
        """Generate response from Ollama"""
        if model is None:
            model = DEFAULT_MODELS[0]  # Use mistral as primary
        
        if not self.available_models:
            return "Error: Ollama is not running. Start it with 'ollama serve'"
        
        if model not in self.available_models:
            logger.warning(f"Model {model} not available. Using {FALLBACK_MODEL}")
            model = FALLBACK_MODEL
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": stream
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', 'No response generated')
            else:
                return f"Error: {response.status_code} - {response.text}"
        
        except requests.exceptions.Timeout:
            return "Error: Request timed out. The model might be processing a large query."
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return f"Error: {str(e)}"
    
    def chat(self, messages: list, model: str = None) -> str:
        """Chat mode with conversation history"""
        if model is None:
            model = DEFAULT_MODELS[0]  # Use mistral as primary
            
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('message', {}).get('content', 'No response generated')
            else:
                return f"Error: {response.status_code}"
        
        except Exception as e:
            logger.error(f"Error in chat mode: {e}")
            return f"Error: {str(e)}"
    
    def list_models(self) -> list:
        """Get available models"""
        return self.available_models


# Initialize agent
agent = OllamaAgent()

# Tool definitions for MCP Server
TOOLS = {
    "ask_ollama": {
        "description": "Ask a question to Ollama AI model (uses deepseek-coder for code tasks, mistral for general tasks)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The prompt or question to send to Ollama"
                },
                "model": {
                    "type": "string",
                    "description": "Model to use - 'deepseek-coder' for code, 'mistral' for general queries, 'codellama' for code generation",
                    "enum": DEFAULT_MODELS
                }
            },
            "required": ["prompt"]
        }
    },
    "chat_ollama": {
        "description": "Chat with Ollama AI using conversation history for multi-turn conversations",
        "inputSchema": {
            "type": "object",
            "properties": {
                "messages": {
                    "type": "array",
                    "description": "Conversation history with role and content",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string", "enum": ["user", "assistant"]},
                            "content": {"type": "string"}
                        },
                        "required": ["role", "content"]
                    }
                },
                "model": {
                    "type": "string",
                    "description": "Model to use - 'deepseek-coder' for code contexts, 'mistral' for general, 'codellama' for code gen",
                    "enum": DEFAULT_MODELS
                }
            },
            "required": ["messages"]
        }
    },
    "list_models": {
        "description": "List available Ollama models currently installed",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    "generate_code": {
        "description": "Generate code using deepseek-coder model (specialized for code generation)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Code generation prompt or description"
                },
                "language": {
                    "type": "string",
                    "description": "Programming language for code generation"
                }
            },
            "required": ["prompt"]
        }
    }
}


def handle_tool_call(tool_name: str, arguments: dict) -> str:
    """Handle MCP tool calls from VS Code Agent"""
    
    if tool_name == "ask_ollama":
        prompt = arguments.get("prompt", "")
        model = arguments.get("model", DEFAULT_MODELS[0])
        logger.info(f"ask_ollama with model={model}")
        return agent.generate(prompt, model)
    
    elif tool_name == "chat_ollama":
        messages = arguments.get("messages", [])
        model = arguments.get("model", DEFAULT_MODELS[0])
        logger.info(f"chat_ollama with model={model}")
        return agent.chat(messages, model)
    
    elif tool_name == "list_models":
        models = agent.list_models()
        logger.info(f"Available models: {models}")
        return json.dumps({
            "models": models,
            "default_models": DEFAULT_MODELS,
            "primary": DEFAULT_MODELS[0] if DEFAULT_MODELS else "none"
        })
    
    elif tool_name == "generate_code":
        prompt = arguments.get("prompt", "")
        language = arguments.get("language", "python")
        logger.info(f"generate_code for {language}")
        code_prompt = f"Generate {language} code for: {prompt}"
        return agent.generate(code_prompt, "deepseek-coder")
    
    else:
        logger.error(f"Unknown tool: {tool_name}")
        return f"Unknown tool: {tool_name}"


def mcp_server_main():
    """Main MCP server loop - handles stdio communication"""
    logger.info("Ollama MCP Server started")
    logger.info(f"Available models: {agent.available_models}")
    logger.info(f"Default models configured: {DEFAULT_MODELS}")
    
    while True:
        try:
            # Read a line from stdin (MCP message)
            line = sys.stdin.readline()
            if not line:
                break
            
            try:
                message = json.loads(line)
                response = {"status": "ok", "result": None}
                
                if message.get("type") == "call_tool":
                    tool_name = message.get("tool", "")
                    arguments = message.get("arguments", {})
                    result = handle_tool_call(tool_name, arguments)
                    response["result"] = result
                
                elif message.get("type") == "ping":
                    response["result"] = "pong"
                
                elif message.get("type") == "get_tools":
                    response["result"] = TOOLS
                
                # Write response to stdout
                print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError as e:
                error_response = {
                    "status": "error",
                    "error": f"Invalid JSON: {str(e)}"
                }
                print(json.dumps(error_response), flush=True)
                
        except KeyboardInterrupt:
            logger.info("Ollama MCP Server stopped")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            error_response = {"status": "error", "error": str(e)}
            print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    # Run as MCP server via stdio
    mcp_server_main()
