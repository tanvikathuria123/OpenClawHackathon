# Career Claw

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
python app.py
```

---

## Connecting Telegram

### 1 — Create a bot

1. Open Telegram and message **@BotFather**
2. Send `/newbot`, follow the prompts, and copy the **bot token** you receive.

### 2 — Get your Chat ID

1. Start a conversation with your new bot (send it any message).
2. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Find `"chat": {"id": <number>}` — that number is your **Chat ID**.

### 3 — Add to `.env`

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_DEFAULT_CHAT_ID=your_chat_id_here
```

The Chat ID field in the UI is optional — leave it blank to use the default from `.env`.
