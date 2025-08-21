import os
from flask import Flask, request, jsonify
import uuid
from supabase import create_client, Client

app = Flask(__name__)

# In-memory storage for conversation state
conversations = {}
PROMPTS = {}

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def load_prompts():
    """Load all prompt files from the prompts directory."""
    prompts_dir = os.path.join('w2_strategy_mcp', 'prompts')
    
    if not os.path.exists(prompts_dir):
        print(f"Warning: Prompts directory not found at {prompts_dir}")
        return
    
    for filename in os.listdir(prompts_dir):
        if filename.endswith('.txt'):
            filepath = os.path.join(prompts_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    PROMPTS[filename] = content
                    print(f"Loaded prompt: {filename}")
            except Exception as e:
                print(f"Error loading {filename}: {e}")

def get_current_prompt_key(step):
    """Get the appropriate prompt file for the current step."""
    prompt_files = {
        0: '01_intro.txt',           # LLM instructions only
        1: '02_job_sensitivity.txt', # First user-facing conversation
        2: '04_investment_alignment.txt',
        3: '05_economic_exposure.txt', 
        4: '06_liquidity_intro.txt',
        5: '07_liquidity_sources.txt',
        6: '08_liquidity_uses.txt',
        7: '09_liquidity_summary.txt',
        8: '10_conclusion.txt'
    }
    return prompt_files.get(step, '10_conclusion.txt')

def personalize_prompt(prompt_template, conversation_data):
    """Personalize prompt with conversation data."""
    if not conversation_data:
        return prompt_template
    
    # Add any personalization logic here
    # For now, return the prompt as-is
    return prompt_template

def store_user_data(conversation_id, step, user_message):
    """Store user response data - placeholder for now."""
    # TODO: Add logic to extract and store specific data points
    # based on the conversation step and user response
    print(f"TODO: Store data from step {step}: {user_message}")
    
    # This is where we'll add the Supabase storage logic
    # to store job_economic_sensitivity, investment_risk_level, etc.

@app.route('/start', methods=['POST'])
def start_conversation():
    """Start a new W2 strategy conversation."""
    conversation_id = str(uuid.uuid4())
    
    # Initialize conversation at step 1 (job_sensitivity), not step 0 (intro)
    # Step 0 (intro) contains LLM instructions that should not be sent to user
    conversations[conversation_id] = {
        'step': 1,  # Start at job sensitivity, skip intro
        'history': [],
        'data': {}
    }
    
    # Get the first user-facing prompt (job sensitivity)
    prompt_key = get_current_prompt_key(1)
    prompt_text = PROMPTS.get(prompt_key, "Let's talk about your work and how it fits into your financial picture.")
    
    # Personalize if needed
    personalized_prompt = personalize_prompt(prompt_text, {})
    
    # Store conversation state
    conversations[conversation_id]['history'].append({
        'speaker': 'bot',
        'text': personalized_prompt
    })
    
    return jsonify({
        'conversation_id': conversation_id,
        'response': personalized_prompt
    })

@app.route('/respond', methods=['POST'])
def respond():
    """Handle user response and return next prompt."""
    data = request.get_json()
    conversation_id = data.get('conversation_id')
    user_message = data.get('message')
    
    if not conversation_id or conversation_id not in conversations:
        return jsonify({'error': 'Invalid conversation ID'}), 400
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    state = conversations[conversation_id]
    current_step = state['step']
    
    # Store user message in history
    state['history'].append({
        'speaker': 'user', 
        'text': user_message
    })
    
    # Store/process user data based on current step
    store_user_data(conversation_id, current_step, user_message)
    
    # Move to next step
    next_step = current_step + 1
    
    # Check if conversation is complete
    if next_step > 8:  # We have 8 conversation steps (1-8)
        final_response = "Thank you for sharing all that information. This gives us a comprehensive picture of your financial strategy."
        state['history'].append({
            'speaker': 'bot',
            'text': final_response
        })
        return jsonify({
            'conversation_id': conversation_id,
            'response': final_response,
            'conversation_complete': True
        })
    
    # Get next prompt
    prompt_key = get_current_prompt_key(next_step)
    prompt_text = PROMPTS.get(prompt_key, "Let's continue our conversation.")
    
    # Personalize based on conversation history
    personalized_prompt = personalize_prompt(prompt_text, state['data'])
    
    # Update conversation state
    state['step'] = next_step
    state['history'].append({
        'speaker': 'bot',
        'text': personalized_prompt
    })
    
    return jsonify({
        'conversation_id': conversation_id,
        'response': personalized_prompt
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'message': 'W2 Strategy MCP Server is running'
    })

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with API information."""
    return jsonify({
        'message': 'W2 Strategy MCP Server',
        'version': '1.0.0',
        'endpoints': {
            'start': '/start - Start a new conversation',
            'respond': '/respond - Continue conversation',
            'health': '/health - Health check'
        }
    })

if __name__ == '__main__':
    print("Loading prompts...")
    load_prompts()
    print(f"Loaded {len(PROMPTS)} prompts")
    
    print("Starting W2 Strategy MCP Server...")
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
