from flask import Flask, render_template, request, jsonify, redirect, session
from dotenv import load_dotenv
from src.components.linkedin import extract_jd
from src.components.websearch import analyze_company
from src.components.telegram import send_telegram, get_history
from src.components.agent import chat as agent_chat, get_history as agent_history, get_session_messages, MODELS, PERSONALITIES
from src.components.gdocs import get_flow, get_credentials, save_token, create_doc
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')

@app.route('/')
@app.route('/home')
def home():
    return render_template('landing_page.html', active='home')

@app.route('/components')
def components():
    return render_template('components.html', active='components')

@app.route('/workflows')
def workflows():
    return render_template('workflows.html', active='workflows')

@app.route('/components/linkedin')
def linkedin_component():
    return render_template('linkedin.html', active='components')

@app.route('/components/websearch')
def websearch_component():
    return render_template('websearch.html', active='components')

@app.route('/api/websearch/analyze', methods=['POST'])
def websearch_analyze():
    data = request.get_json()
    company = (data or {}).get('company', '').strip()
    title = (data or {}).get('title', '').strip()
    location = (data or {}).get('location', '').strip()
    jd = (data or {}).get('jd', '').strip()
    if not company:
        return jsonify({'success': False, 'error': 'Company name is required'})
    try:
        analysis = analyze_company(company, title, location, jd)
        return jsonify({'success': True, 'analysis': analysis})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/components/telegram')
def telegram_component():
    return render_template('telegram.html', active='components', history=get_history())

@app.route('/api/telegram/send', methods=['POST'])
def telegram_send():
    data = request.get_json()
    message = (data or {}).get('message', '').strip()
    chat_id = (data or {}).get('chat_id', '').strip() or None
    if not message:
        return jsonify({'success': False, 'error': 'Message is required'})
    try:
        send_telegram(message, chat_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/telegram/history')
def telegram_history():
    return jsonify({'history': get_history()})

@app.route('/api/linkedin/extract', methods=['POST'])
def linkedin_extract():
    data = request.get_json()
    url = (data or {}).get('url', '').strip()
    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'})
    try:
        jd = extract_jd(url)
        return jsonify({'success': True, 'jd': jd})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/components/agent')
def agent_component():
    return render_template('agent.html', active='components',
                           history=agent_history(), models=MODELS,
                           personalities=list(PERSONALITIES.keys()))

@app.route('/api/agent/chat', methods=['POST'])
def agent_chat_api():
    data = request.get_json()
    session_id = (data or {}).get('session_id', '').strip()
    message = (data or {}).get('message', '').strip()
    model = (data or {}).get('model', MODELS[0])
    personality = (data or {}).get('personality', 'None')
    if not message:
        return jsonify({'success': False, 'error': 'Message is required'})
    try:
        result = agent_chat(session_id, message, model, personality)
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/agent/session/<session_id>')
def agent_session(session_id):
    return jsonify({'success': True, 'messages': get_session_messages(session_id)})

@app.route('/api/agent/history')
def agent_history_api():
    return jsonify({'history': agent_history()})

@app.route('/components/gdocs')
def gdocs_component():
    return render_template('gdocs.html', active='components', connected=bool(get_credentials()))

GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:7200/auth/google/callback')

@app.route('/auth/google')
def auth_google():
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    flow = get_flow(GOOGLE_REDIRECT_URI)
    auth_url, state = flow.authorization_url(access_type='offline', prompt='consent')
    session['oauth_state'] = state
    return redirect(auth_url)

@app.route('/auth/google/callback')
def auth_google_callback():
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    flow = get_flow(GOOGLE_REDIRECT_URI)
    flow.fetch_token(authorization_response=request.url)
    save_token(flow.credentials.to_json())
    return redirect('/components/gdocs')

@app.route('/auth/google/disconnect')
def auth_google_disconnect():
    if os.path.exists('data/google_token.json'):
        os.remove('data/google_token.json')
    return redirect('/components/gdocs')

@app.route('/api/gdocs/save', methods=['POST'])
def gdocs_save():
    data = request.get_json()
    name = (data or {}).get('name', 'Untitled Document').strip()
    latex = (data or {}).get('latex', '').strip()
    if not latex:
        return jsonify({'success': False, 'error': 'No content to save'})
    try:
        url = create_doc(name, latex)
        return jsonify({'success': True, 'url': url})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=7200)
