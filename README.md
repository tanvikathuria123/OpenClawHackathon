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

---

## Connecting Google Docs

### 1 — Create a Google Cloud project

1. Go to [https://console.cloud.google.com](https://console.cloud.google.com) and create a new project.
2. In the left menu go to **APIs & Services → Library**.
3. Search for **Google Docs API** and click **Enable**.

### 2 — Create OAuth 2.0 credentials

1. Go to **APIs & Services → Credentials**.
2. Click **Create Credentials → OAuth client ID**.
3. If prompted, configure the **OAuth consent screen** first:
   - User type: **External** → fill in app name and your email → Save.
   - Add scope: `https://www.googleapis.com/auth/documents`
   - Add your email as a **Test user**.
4. Back in Credentials → Create OAuth client ID:
   - Application type: **Web application**
   - Authorised redirect URI: `http://localhost:7200/auth/google/callback`  
     *(change the host/port if deploying elsewhere)*
5. Click **Create**, then **Download JSON**.

### 3 — Place the credentials file

Rename the downloaded file to `google_credentials.json` and put it in the `data/` folder:

```
data/google_credentials.json
```

### 4 — Connect inside the app

1. Run the app (`python app.py`).
2. Open **Components → Google Docs**.
3. Click **Connect Google** — you will be redirected to Google's consent screen.
4. Approve access. You are redirected back and the button turns green.
5. Tokens are stored in `data/google_token.json` — no need to reconnect on restart.
