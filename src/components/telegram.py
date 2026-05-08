import os, json, requests
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_DEFAULT_CHAT_ID = os.getenv('TELEGRAM_DEFAULT_CHAT_ID')
HISTORY_FILE = 'outputs/telegram_history.json'


def send_telegram(message, chat_id=None):
    chat_id = chat_id or TELEGRAM_DEFAULT_CHAT_ID
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={'chat_id': chat_id, 'text': message}, timeout=10)
    resp.raise_for_status()
    _save_history(message, chat_id)
    return resp.json()


def get_history():
    try:
        with open(HISTORY_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_history(message, chat_id):
    os.makedirs('outputs', exist_ok=True)
    history = get_history()
    history.insert(0, {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'message': message,
        'chat_id': chat_id,
    })
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history[:20], f)
