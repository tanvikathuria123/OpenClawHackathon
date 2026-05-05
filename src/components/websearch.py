import os
import re
import json
import requests
from bs4 import BeautifulSoup
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.prompts.websearch import SYSTEM_PROMPT, build_user_prompt

_PREFS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "preferences.txt")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _ddg_overview(company: str) -> str:
    """DuckDuckGo Instant Answer — reliable, never rate-limited."""
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": company, "format": "json", "no_html": 1, "skip_disambig": 1},
            headers=_HEADERS, timeout=8
        )
        data = resp.json()
        parts = []
        if data.get("Abstract"):
            parts.append(data["Abstract"])
        for topic in data.get("RelatedTopics", [])[:2]:
            if isinstance(topic, dict) and topic.get("Text"):
                parts.append(topic["Text"])
        return "\n".join(parts)
    except Exception:
        return ""


def _teamblind(company: str) -> str:
    """Scrape TeamBlind company page — ratings, reviews, salary data."""
    try:
        slug = company.strip().replace(" ", "-")
        resp = requests.get(
            f"https://www.teamblind.com/company/{slug}",
            headers=_HEADERS, timeout=10
        )
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        lines = [l.strip() for l in soup.get_text(separator="\n").splitlines() if l.strip()]

        parts = []

        # ── Overall rating: find first X.Y float in top 10 lines, count 2 lines after
        for i, line in enumerate(lines[:10]):
            if re.match(r"^\d\.\d$", line):
                count_candidate = lines[i + 2] if i + 2 < len(lines) else "?"
                review_count = count_candidate if count_candidate.isdigit() else "?"
                parts.append(f"TeamBlind Rating: {line}/5 ({review_count} reviews)")
                break

        # ── Overview block: Website / Industry / Locations / Size / Salary / Description
        overview_fields = ["Website", "Industry", "Locations", "Founded", "Size", "Salary"]
        overview_parts = []
        for i, line in enumerate(lines):
            if line in overview_fields and i + 1 < len(lines):
                overview_parts.append(f"{line}: {lines[i+1]}")
            if line.startswith(f"{company} is") or line.startswith("Remitly is"):
                overview_parts.append(f"Description: {line}")
        if overview_parts:
            parts.append("Overview:\n" + "\n".join(overview_parts))

        # ── Discussion post titles (between "Remitly Discussions" and "View All Posts")
        try:
            disc_start = next(i for i, l in enumerate(lines) if "Discussions" in l and company in lines[max(0,i-2):i+2])
            disc_end = next(i for i, l in enumerate(lines) if l == "View All Posts")
            disc_lines = lines[disc_start + 1:disc_end]
            # Filter to just post titles (skip dates, usernames, nums)
            titles = [l for l in disc_lines if len(l) > 10 and not l[0].isdigit()
                      and not l.startswith("$") and "/" not in l[:5]
                      and l not in ["Interview","Layoffs","Culture","WLB","Tech Industry","AMA","Software Engineering Career","2026 Tax"]]
            if titles:
                parts.append("Recent Discussions:\n" + "\n".join(f"- {t}" for t in titles[:8]))
        except StopIteration:
            pass

        # ── Ratings breakdown + review (between "Company Reviews" and "View All Reviews")
        try:
            rev_start = next(i for i, l in enumerate(lines) if l == "Company Reviews")
            rev_end = next(i for i, l in enumerate(lines) if l == "View All Reviews")
            rev_lines = lines[rev_start:rev_end]

            # Sub-ratings (pattern: number, then category label)
            rating_cats = ["Career Growth","Work Life Balance","Compensation / Benefits","Company Culture","Management"]
            sub_ratings = []
            for i, l in enumerate(rev_lines):
                if l in rating_cats and i > 0:
                    score_parts = rev_lines[i-1:i+1]
                    # Score might be split across two lines (e.g. "2" and ".0")
                    if i >= 2 and rev_lines[i-2] in [str(n) for n in range(1, 6)]:
                        score = rev_lines[i-2] + rev_lines[i-1] if rev_lines[i-1].startswith(".") else rev_lines[i-1]
                    else:
                        score = rev_lines[i-1]
                    sub_ratings.append(f"  {l}: {score}")
            if sub_ratings:
                parts.append("Ratings breakdown:\n" + "\n".join(sub_ratings))

            # Review text (Pros/Cons)
            pros_i = next((i for i, l in enumerate(rev_lines) if l == "Pros"), None)
            cons_i = next((i for i, l in enumerate(rev_lines) if l == "Cons"), None)
            review_title = next((l for l in rev_lines if l.startswith('"') or l.startswith("Going") or l.startswith("Don")), None)
            if review_title:
                parts.append(f'Top review: "{review_title}"')
            if pros_i is not None and pros_i + 1 < len(rev_lines):
                parts.append(f"Pros: {rev_lines[pros_i + 1]}")
            if cons_i is not None and cons_i + 1 < len(rev_lines):
                parts.append(f"Cons: {rev_lines[cons_i + 1]}")
        except StopIteration:
            pass

        # ── Salary stats (median, percentiles)
        try:
            sal_i = next(i for i, l in enumerate(lines) if "Salaries and Total Compensation" in l)
            sal_block = lines[sal_i:sal_i + 15]
            salary_text = " ".join(sal_block)
            parts.append(f"TeamBlind Salary Data: {salary_text}")
        except StopIteration:
            pass

        return "\n\n".join(parts) if parts else ""
    except Exception:
        return ""


def _levels_fyi(company: str) -> str:
    """Scrape Levels.fyi company salary page — extracts JSON-LD FAQ + salary range text."""
    try:
        slug = company.strip().lower().replace(" ", "-")
        resp = requests.get(
            f"https://www.levels.fyi/companies/{slug}/salaries/",
            headers=_HEADERS, timeout=10
        )
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")

        parts = []

        # Extract JSON-LD FAQ (most reliable — structured salary Q&A)
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if data.get("@type") == "FAQPage":
                    for item in data.get("mainEntity", []):
                        q = item.get("name", "")
                        a = item.get("acceptedAnswer", {}).get("text", "")
                        if q and a:
                            parts.append(f"Q: {q}\nA: {a}")
            except Exception:
                continue

        # Also grab visible salary range text
        page_text = soup.get_text(separator="\n", strip=True)
        lines = page_text.splitlines()
        salary_lines = []
        capture = False
        for line in lines:
            if company.lower() in line.lower() and "salary" in line.lower():
                capture = True
            if capture:
                salary_lines.append(line)
            if len(salary_lines) > 40:
                break
        if salary_lines:
            parts.append("\n".join(salary_lines))

        return "\n\n".join(parts)[:3000]
    except Exception:
        return ""


def _gather_context(company: str, title: str, location: str) -> str:
    sections = []

    overview = _ddg_overview(company)
    if overview:
        sections.append(f"=== Company Overview (DuckDuckGo) ===\n{overview}")

    blind = _teamblind(company)
    if blind:
        sections.append(f"=== TeamBlind ===\n{blind}")

    levels = _levels_fyi(company)
    if levels:
        sections.append(f"=== Levels.fyi Salary Data ===\n{levels}")

    if not sections:
        sections.append(
            f"No live data retrieved. Use your training knowledge about {company} "
            f"to analyze this {title} role in {location}."
        )

    return "\n\n".join(sections)


def analyze_company(company: str, title: str, location: str, jd: str) -> str:
    if not company.strip():
        raise ValueError("Company name is required.")

    context = _gather_context(company, title, location)

    with open(_PREFS_PATH) as f:
        preferences = f.read()

    llm = ChatOpenAI(
        model="anthropic/claude-sonnet-4-5",
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base="https://openrouter.ai/api/v1",
        default_headers={"HTTP-Referer": "https://careerclaw.app"},
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=build_user_prompt(company, title, location, jd, context, preferences)),
    ]

    response = llm.invoke(messages)
    return response.content
