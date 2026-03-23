"""
Example: Using Ollama Agent in Flask
Demonstrates how to integrate the Ollama MCP agent with your Flask app
"""

from flask import Blueprint, request, jsonify
from ollama_mcp_server import agent
import logging

logger = logging.getLogger(__name__)

# Create a blueprint for AI features
ai_blueprint = Blueprint('ai', __name__, url_prefix='/api/ai')


@ai_blueprint.route('/ask', methods=['POST'])
def ask_ai():
    """
    Simple Q&A endpoint
    
    Request:
        POST /api/ai/ask
        {
            "question": "How many coaches are in the database?",
            "model": "llama2"  # optional
        }
    """
    try:
        data = request.get_json()
        question = data.get('question', '')
        model = data.get('model', 'llama2')
        
        if not question:
            return jsonify({'error': 'No question provided'}), 400
        
        response = agent.generate(question, model=model)
        
        return jsonify({
            'question': question,
            'answer': response,
            'model': model
        })
    
    except Exception as e:
        logger.error(f"Error in ask_ai: {e}")
        return jsonify({'error': str(e)}), 500


@ai_blueprint.route('/chat', methods=['POST'])
def chat_ai():
    """
    Chat endpoint with conversation history
    
    Request:
        POST /api/ai/chat
        {
            "messages": [
                {"role": "user", "content": "What's a coach?"},
                {"role": "assistant", "content": "..."},
                {"role": "user", "content": "How are they managed?"}
            ],
            "model": "llama2"  # optional
        }
    """
    try:
        data = request.get_json()
        messages = data.get('messages', [])
        model = data.get('model', 'llama2')
        
        if not messages:
            return jsonify({'error': 'No messages provided'}), 400
        
        response = agent.chat(messages, model=model)
        
        return jsonify({
            'response': response,
            'model': model
        })
    
    except Exception as e:
        logger.error(f"Error in chat_ai: {e}")
        return jsonify({'error': str(e)}), 500


@ai_blueprint.route('/models', methods=['GET'])
def list_models():
    """
    Get available Ollama models
    
    Response:
        {
            "models": ["llama2", "mistral", "neural-chat"]
        }
    """
    try:
        models = agent.list_models()
        return jsonify({'models': models})
    
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return jsonify({'error': str(e)}), 500


@ai_blueprint.route('/analyze-database', methods=['POST'])
def analyze_database():
    """
    Ask AI to analyze database structure
    
    Example usage:
        POST /api/ai/analyze-database
        {"topic": "coach salary calculations"}
    """
    try:
        data = request.get_json()
        topic = data.get('topic', 'database structure')
        
        prompt = f"""
        Analyze the following topic in the Academy Dashboard database:
        Topic: {topic}
        
        Consider:
        1. Related database models
        2. Key relationships
        3. Potential optimization points
        4. Common issues or edge cases
        """
        
        response = agent.generate(prompt, model='llama2')
        
        return jsonify({
            'topic': topic,
            'analysis': response
        })
    
    except Exception as e:
        logger.error(f"Error analyzing database: {e}")
        return jsonify({'error': str(e)}), 500


# Example: How to use in your main app.py
"""
from flask import Flask
from ollama_example import ai_blueprint

app = Flask(__name__)
app.register_blueprint(ai_blueprint)

# Now you have:
# POST /api/ai/ask
# POST /api/ai/chat
# GET /api/ai/models
# POST /api/ai/analyze-database

if __name__ == '__main__':
    app.run(debug=True)
"""

# Example: Use in a route
"""
@app.route('/dashboard')
def dashboard():
    # Get AI insights
    from ollama_mcp_server import agent
    
    coaches_prompt = "Summarize key information about managing multiple coaches efficiently"
    insight = agent.generate(coaches_prompt)
    
    return render_template('dashboard.html', ai_insight=insight)
"""
