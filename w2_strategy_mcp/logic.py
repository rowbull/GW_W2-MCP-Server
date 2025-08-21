import os
from flask import Flask, request, jsonify
import uuid
from supabase import create_client, Client
import json

app = Flask(__name__)

# In-memory storage for conversation state
conversations = {}
PROMPTS = {}

# Supabase configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def load_prompts():
    """Load all prompt files from the prompts directory"""
    prompts_dir = os.path.join('w2_strategy_mcp', 'prompts')
    
    for filename in os.listdir(prompts_dir):
        if filename.endswith('.txt'):
            with open(os.path.join(prompts_dir, filename), 'r') as f:
                PROMPTS[filename] = f.read()

def get_current_prompt_key(step):
    """Get the prompt file key for the current step"""
    prompt_map = {
        1: '02_job_sensitivity.txt', 
        2: '04_investment_alignment.txt',
        3: '05_economic_exposure.txt',
        4: '06_liquidity_intro.txt',
        5: '07_liquidity_sources.txt',
        6: '08_liquidity_uses.txt',
        7: '09_liquidity_summary.txt',
        8: '10_conclusion.txt'
    }
    return prompt_map.get(step, '10_conclusion.txt')

@app.route('/start', methods=['POST'])
def start_conversation():
    """Initialize a new conversation - return prompt instructions like yesterday's MCP"""
    conversation_id = str(uuid.uuid4())
    
    # Start at step 1 (job sensitivity), skip step 0 (intro)
    conversations[conversation_id] = {
        'step': 1,
        'history': [],
        'data': {},
        'user_context': request.json.get('conversation_context', {})
    }
    
    # Get the prompt for job sensitivity
    prompt_key = get_current_prompt_key(1)
    instructions = PROMPTS.get(prompt_key, "Let's talk about your job and financial situation.")
    
    # Return in the same format as yesterday's working MCP
    return jsonify({
        'conversation_id': conversation_id,
        'instructions': instructions,
        'session_type': 'w2_strategy',
        'step': 1,
        'tools_to_use': ['store_user_fact']
    })

@app.route('/respond', methods=['POST'])
def respond():
    """Continue conversation - return next prompt instructions"""
    data = request.json
    conversation_id = data.get('conversation_id')
    message = data.get('message', '')
    
    if conversation_id not in conversations:
        return jsonify({'error': 'Conversation not found'}), 404
    
    conversation = conversations[conversation_id]
    conversation['history'].append({'user': message})
    
    # Advance to next step
    current_step = conversation['step']
    if current_step < 8:
        conversation['step'] += 1
    
    # Get next prompt
    prompt_key = get_current_prompt_key(conversation['step'])
    instructions = PROMPTS.get(prompt_key, "Thank you for that information.")
    
    return jsonify({
        'instructions': instructions,
        'session_type': 'w2_strategy', 
        'step': conversation['step'],
        'tools_to_use': ['store_user_fact']
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'W2 Strategy MCP'})

if __name__ == '__main__':
    load_prompts()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=True)
