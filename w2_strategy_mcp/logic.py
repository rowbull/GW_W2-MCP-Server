import os
from flask import Flask, request, jsonify
import uuid

app = Flask(__name__)

# In-memory storage for conversation state
conversations = {}
PROMPTS = {}

def load_prompts():
    """Load all prompts from the prompts directory into memory."""
    global PROMPTS
    prompt_dir = os.path.join(os.path.dirname(__file__), 'prompts')
    # Ensure consistent order by sorting filenames
    for filename in sorted(os.listdir(prompt_dir)):
        if filename.endswith('.txt'):
            key = filename.split('.')[0]
            with open(os.path.join(prompt_dir, filename), 'r', encoding='utf-8') as f:
                PROMPTS[key] = f.read()

def get_current_prompt_key(step):
    """Gets the prompt key for the current step based on sorted order."""
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
        'data': {} # To store user's answers
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
    """Rudimentary logic to extract and store data from user message based on the new flow."""
    step = state['step']
    # The step number corresponds to the prompt the user is *responding to*.
    if step == 1: # Response to 02_job_sensitivity
        state['data']['job_sensitivity_raw'] = user_message
    elif step == 2: # Response to 04_investment_alignment
        state['data']['investment_alignment_raw'] = user_message
    elif step == 3: # Response to 05_economic_exposure
        state['data']['homeowner_raw'] = user_message
    elif step == 5: # Response to 07_liquidity_sources
        state['data']['liquidity_sources_raw'] = user_message
    elif step == 6: # Response to 08_liquidity_uses
        state['data']['liquidity_uses_raw'] = user_message

def personalize_prompt(prompt_text, state):
    """Personalize prompts based on stored conversation data."""
    step = state['step'] # The step number corresponds to the prompt we are *about to send*.

    # Personalize economic exposure summary (the new step 3)
    if step == 3: # This is for prompt '05_economic_exposure'
        job_summary = state['data'].get('job_sensitivity_raw', '...')
        invest_summary = state['data'].get('investment_alignment_raw', '...')

        # This prompt combines insights and asks a new question.
        prompt_text = (
            f"Thank you for sharing that. We've discussed:\n"
            f"- Your job's economic sensitivity: '{job_summary[:50]}...'\n"
            f"- Your investment alignment: '{invest_summary[:50]}...'\n\n"
            "The final piece of the economic exposure puzzle is real estate. For many people, their home is their largest asset, and it's also tied to the local economy.\n\n"
            "Do you own your primary residence? (e.g., 'Yes, I own a home' or 'No, I rent')"
        )

    # Personalize liquidity summary (the new step 7)
    if step == 7: # This is for prompt '09_liquidity_summary'
        sources_summary = state['data'].get('liquidity_sources_raw', '...')
        prompt_text = (
            f"It's a different way of thinking, for sure. So let's bring it all together.\n\n"
            f"On one hand, you have your liquidity sources, which you described as: '{sources_summary[:100]}...'\n"
            f"On the other, you have potential needs beyond just job loss, like health, property, or family emergencies.\n\n"
            "How does your current liquidity stack up against this broader view of potential needs? Do you see any gaps, or maybe opportunities to be more efficient?\n\n"
            "This is the core of strategic liquidity: matching the right type of capital to the right type of risk."
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

    # Store data from the user's response to the *previous* prompt
    store_user_data(state, user_message)
    state['history'].append({'speaker': 'user', 'text': user_message})

    # Increment step to get the *next* prompt
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
        # Use the final conclusion prompt if we're at the end
        conclusion_key = get_current_prompt_key(len(PROMPTS) - 1)
        conclusion_text = PROMPTS[conclusion_key]
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
