import os, re, queue, threading, traceback, time
import requests as _requests
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.components.linkedin import extract_jd
from src.components.websearch import analyze_company
from src.components.gdocs import create_doc
from src.components.telegram import send_telegram
from src.prompts.resume_optimizer import SYSTEM_PROMPT, build_user_prompt

RESUME_PATH = Path('base_resume.txt')
_job_queue = queue.Queue()


def _llm():
    return ChatOpenAI(
        model="anthropic/claude-sonnet-4-5",
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base="https://openrouter.ai/api/v1",
        max_tokens=4096,
    )


def _parse_jd_fields(jd_text):
    company = title = location = ""
    for line in jd_text.split('\n'):
        l = line.strip().lstrip('#').strip()
        if not company and re.search(r'\bcompany\b', l, re.I) and ':' in l:
            company = re.sub(r'^[^:]+:\s*\*?', '', l).strip('*').strip()
        if not title and re.search(r'\b(?:job\s+)?title\b', l, re.I) and ':' in l:
            title = re.sub(r'^[^:]+:\s*\*?', '', l).strip('*').strip()
        if not location and re.search(r'\blocation\b', l, re.I) and ':' in l:
            location = re.sub(r'^[^:]+:\s*\*?', '', l).strip('*').strip()
    return company or "Unknown Company", title or "Unknown Title", location or ""


def _extract_latex(text):
    m = re.search(r'```(?:latex|tex)?\n([\s\S]+?)\n```', text)
    return m.group(1) if m else text


def run_workflow1(url, chat_id):
    print(f"[workflow1] START: {url}")
    send_telegram(f"⏳ Processing: {url}", chat_id)

    print("[workflow1] step 1/5: extracting JD from LinkedIn...")
    jd = extract_jd(url)
    company, title, location = _parse_jd_fields(jd)
    print(f"[workflow1] step 1 done: {title} @ {company} ({location})")
    send_telegram(f"\U0001f4cb Got JD: {title} @ {company}. Researching company...", chat_id)

    print("[workflow1] step 2/5: researching company via web search...")
    company_info = analyze_company(company, title, location, jd)
    print("[workflow1] step 2 done")
    send_telegram("✍️ Optimizing your resume...", chat_id)

    print("[workflow1] step 3/5: optimizing resume with LLM...")
    base_resume = RESUME_PATH.read_text()
    resp = _llm().invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=build_user_prompt(jd, company_info, base_resume))
    ])
    optimized_latex = _extract_latex(resp.content)
    print("[workflow1] step 3 done")

    print("[workflow1] step 4/5: saving to Google Docs...")
    doc_title = f"{company} - {title}"
    doc_url = create_doc(doc_title, optimized_latex)
    print(f"[workflow1] step 4 done: {doc_url}")

    print("[workflow1] step 5/5: sending result to Telegram...")
    send_telegram(
        f"✅ Resume ready!\n\n\U0001f4c4 {doc_title}\n{doc_url}\n\n\U0001f3e2 Company Insights:\n{company_info[:600]}",
        chat_id
    )
    print("[workflow1] DONE")


def _worker():
    while True:
        url, chat_id = _job_queue.get()
        print(f"[worker] picked up job: {url[:80]}")
        try:
            run_workflow1(url, chat_id)
        except Exception as e:
            print(f"[worker] ERROR: {e}")
            traceback.print_exc()
            send_telegram(f"❌ Error on {url[:60]}: {str(e)}", chat_id)
        finally:
            _job_queue.task_done()


def start_worker():
    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def enqueue(url, chat_id):
    _job_queue.put((url, chat_id))
    return _job_queue.qsize()


def _poll_telegram():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    offset = None
    print("[telegram poll] started — waiting for messages...")
    while True:
        try:
            params = {'timeout': 30, 'allowed_updates': ['message']}
            if offset is not None:
                params['offset'] = offset
            resp = _requests.get(
                f"https://api.telegram.org/bot{token}/getUpdates",
                params=params, timeout=35
            )
            for update in resp.json().get('result', []):
                offset = update['update_id'] + 1
                msg = update.get('message', {})
                text = msg.get('text', '').strip()
                chat_id = str(msg.get('chat', {}).get('id', ''))
                print(f"[telegram poll] received: {text[:80]!r} from chat_id={chat_id}")
                if re.search(r'linkedin\.com/jobs', text):
                    pos = enqueue(text, chat_id)
                    print(f"[telegram poll] LinkedIn URL enqueued, queue size={pos}")
                    send_telegram(f"📥 LinkedIn URL queued (position {pos}). Processing...", chat_id)
                else:
                    print("[telegram poll] not a LinkedIn jobs URL, ignoring")
        except Exception as e:
            print(f"[telegram poll] error: {e}")
            time.sleep(5)


def start_polling():
    t = threading.Thread(target=_poll_telegram, daemon=True)
    t.start()
