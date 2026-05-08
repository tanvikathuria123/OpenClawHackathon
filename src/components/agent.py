import os, json
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

HISTORY_FILE = "outputs/agent_history.json"
MODELS = [
    "anthropic/claude-sonnet-4-5",
    "anthropic/claude-haiku-4-5",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "google/gemini-flash-1.5",
    "meta-llama/llama-3.3-70b-instruct",
    "mistralai/mistral-7b-instruct",
]
PERSONALITIES = {
    "None": None,
    "Career Coach": "You are a seasoned career coach helping with job searches, resume writing, and interview prep. Be concise and actionable.",
}

_sessions = {}


def _load():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return []


def _persist(session_id, data):
    history = [h for h in _load() if h["id"] != session_id]
    history.insert(0, data)
    os.makedirs("outputs", exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history[:20], f, indent=2)


def get_history():
    return _load()


def get_session_messages(session_id):
    if session_id in _sessions:
        return _sessions[session_id]["messages"]
    for h in _load():
        if h["id"] == session_id:
            return h["messages"]
    return []


def chat(session_id, message, model, personality):
    if session_id not in _sessions:
        _sessions[session_id] = {
            "id": session_id,
            "model": model,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "messages": [],
        }

    session = _sessions[session_id]
    llm = ChatOpenAI(
        model=model,
        api_key=os.environ["OPENROUTER_API_KEY"],
        base_url="https://openrouter.ai/api/v1",
    )

    lc_msgs = []
    sys_prompt = PERSONALITIES.get(personality)
    if sys_prompt:
        lc_msgs.append(SystemMessage(content=sys_prompt))
    for m in session["messages"]:
        cls = HumanMessage if m["role"] == "user" else AIMessage
        lc_msgs.append(cls(content=m["content"]))
    lc_msgs.append(HumanMessage(content=message))

    response = llm.invoke(lc_msgs)

    session["messages"].append({"role": "user", "content": message})
    session["messages"].append({"role": "assistant", "content": response.content})

    usage = getattr(response, "usage_metadata", {}) or {}
    in_tok = usage.get("input_tokens", 0)
    out_tok = usage.get("output_tokens", 0)

    _persist(session_id, session)
    return {"reply": response.content, "in_tokens": in_tok, "out_tokens": out_tok}
