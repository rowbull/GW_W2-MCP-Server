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
    """Load all prompts from the prompts directory into memory."""
    global PROMPTS
    prompt_dir = os.path.join(os.path.dirname(__file__), 'prompts')
    for filename in sorted(os.listdir(prompt_dir)):
        if filename.endswith('.txt'):
            key = filename.split('.')[0]
            with open(os.path.join(prompt_dir, filename), 'r', encoding='utf-8') as f:
                PROMPTS[key] = f.read()

def get_current_prompt_key(step):
    """Gets the prompt key for the current step."""
    prompt_keys = sorted(PROMPTS.keys())
    if 0 <= step < len(prompt_keys):
        return prompt_keys[step]
    return None

@app.route('/start', methods=['POST'])
def start_conversation():
    """Starts a new conversation and returns the introductory prompt."""
    conversation_id = str(uuid.uuid4())
    conversations[conversation_id] = {
        'step': 0,
        'history': [],
        'data': {}
    }

    prompt_key = get_current_prompt_key(0)
    prompt_text = PROMPTS[prompt_key]

    state = conversations[conversation_id]
    state['history'].append({'speaker': 'bot', 'text': prompt_text})

    return jsonify({
        'conversation_id': conversation_id,
        'response': prompt_text
    })

def store_user_data(state, user_message):
    """Extract and store data from user message to Supabase."""
    step = state['step']
    conversation_id = state.get('conversation_id')
    
    # Store the response for this step
    if step == 1:  # Job sensitivity response
        state['data']['job_sensitivity_raw'] = user_message
        # TODO: Parse and determine job_economic_sensitivity (1-3 scale)
        
    elif step == 2:  # Geographic risk response
        state['data']['geographic_risk_raw'] = user_message
        
    elif step == 3:  # Investment alignment response
        state['data']['investment_alignment_raw'] = user_message
        
    elif step == 6:  # Liquidity sources response
        state['data']['liquidity_sources_raw'] = user_message
        
    elif step == 7:  # Liquidity uses response
        state['data']['liquidity_uses_raw'] = user_message

    # Save to Supabase when we have meaningful data
    if conversation_id and len(state['data']) > 0:
        try:
            # For now, just store the conversation data
            # TODO: Parse responses and populate specific columns
            result = supabase.table('user_profile_data').upsert({
                'id': conversation_id,  # Use conversation_id as primary key
                'conversation_data': state['data']
            }).execute()
        except Exception as e:
            print(f"Error saving to Supabase: {e}")

def personalize_prompt(prompt_text, state):
    """Personalize prompts based on stored conversation data."""
    step = state['step']

    if step == 4:  # Concentration summary
        job_summary = state['data'].get('job_sensitivity_raw', '...')
        geo_summary = state['data'].get('geographic_risk_raw', '...')
        invest_summary = state['data'].get('investment_alignment_raw', '...')

        prompt_text = (
            f"Thank you for sharing that. We've discussed:\n"
            f"- Your job's economic sensitivity\n"
            f"- Your geographic concentration\n"
            f"- Your investment alignment\n\n"
            "This understanding of risk concentration leads directly to our next topic: "
            "building a sophisticated liquidity strategy. Ready to move on to that?"
        )

    elif step == 8:  # Liquidity summary
        prompt_text = (
            "Let's bring it all together. You've shared your liquidity sources and "
            "we've talked about potential uses beyond just job loss.\n\n"
            "How does your current liquidity stack up against this broader view of potential needs? "
            "Do you see any gaps, or opportunities to be more efficient?"
        )

    return prompt_text

@app.route('/respond', methods=['POST'])
def respond():
    """Handles a user's response and returns the next prompt."""
    data = request.get_json()
    conversation_id = data.get('conversation_id')
    user_message = data.get('message')

    if not conversation_id or conversation_id not in conversations:
        return jsonify({'error': 'Invalid conversation ID'}), 400

    state = conversations[conversation_id]
    state['conversation_id'] = conversation_id
    state['history'].append({'speaker': 'user', 'text': user_message})

    # Store data from previous step's response
    store_user_data(state, user_message)

    # Increment step to get the next prompt
    state['step'] += 1
    current_step_index = state['step']

    next_prompt_key = get_current_prompt_key(current_step_index)

    if next_prompt_key:
        prompt_text = PROMPTS[next_prompt_key]
        prompt_text = personalize_prompt(prompt_text, state)

        state['history'].append({'speaker': 'bot', 'text': prompt_text})

        return jsonify({
            'conversation_id': conversation_id,
            'response': prompt_text
        })
    else:
        # End of conversation
        conclusion_text = "Thank you for this thoughtful conversation about your financial strategy."
        return jsonify({
            'conversation_id': conversation_id,
            'response': conclusion_text
        })

def main():
    """Main function to load prompts and run the Flask app."""
    load_prompts()
    app.run(host='0.0.0.0', port=8080, debug=True)

if __name__ == '__main__':
    main()
