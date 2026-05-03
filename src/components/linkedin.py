import os
import re
import json
import requests
from bs4 import BeautifulSoup
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.prompts.linkedin_jd import SYSTEM_PROMPT, build_user_prompt

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

JD_SELECTORS = [
    ".show-more-less-html__markup",
    ".description__text",
    ".jobs-description__content",
    ".jobs-description-content__text",
    "[class*='description__text']",
    "[class*='jobs-description']",
]

TITLE_SELECTORS = [
    "h1.top-card-layout__title",
    "h1.t-24",
    ".top-card-layout__title",
    ".job-details-jobs-unified-top-card__job-title h1",
    "h1",
]

COMPANY_SELECTORS = [
    ".topcard__org-name-link",
    ".top-card-layout__second-line a",
    ".jobs-unified-top-card__company-name a",
    ".job-details-jobs-unified-top-card__company-name a",
]


def extract_job_id(url: str) -> str | None:
    # Matches numeric job IDs in LinkedIn URLs
    match = re.search(r"(\d{7,})", url)
    return match.group(1) if match else None


def validate_url(url: str):
    if "linkedin.com" not in url:
        raise ValueError("URL must be a LinkedIn URL.")
    if "/jobs/search" in url or "/jobs/collections" in url:
        raise ValueError(
            "This looks like a search results URL. Please open a specific job posting "
            "and paste that URL instead (it should contain /jobs/view/)."
        )


def _text_from_soup(soup: BeautifulSoup, selectors: list) -> str:
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            return el.get_text(separator="\n", strip=True)
    return ""


def scrape_via_guest_api(job_id: str) -> str:
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code != 200 or not resp.text.strip():
        return ""
    soup = BeautifulSoup(resp.text, "html.parser")
    return _parse_soup(soup)


def scrape_via_direct_url(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
    if resp.status_code == 999:
        raise ValueError("LinkedIn blocked the request (status 999). Try the job view URL directly from your browser.")
    resp.raise_for_status()

    if "authwall" in resp.url or ("login" in resp.url and "jobs" not in resp.url):
        raise ValueError("LinkedIn redirected to login. Make sure the job posting is public.")

    soup = BeautifulSoup(resp.text, "html.parser")

    # Try JSON-LD structured data first
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if data.get("@type") == "JobPosting":
                return _parse_jsonld(data)
        except (json.JSONDecodeError, AttributeError):
            continue

    return _parse_soup(soup)


def _parse_jsonld(data: dict) -> str:
    parts = []
    if data.get("title"):
        parts.append(f"Title: {data['title']}")
    org = data.get("hiringOrganization", {})
    if org.get("name"):
        parts.append(f"Company: {org['name']}")
    loc = data.get("jobLocation")
    if loc:
        if isinstance(loc, list):
            loc = loc[0]
        addr = loc.get("address", {})
        location_str = ", ".join(filter(None, [
            addr.get("addressLocality"), addr.get("addressRegion"), addr.get("addressCountry")
        ]))
        if location_str:
            parts.append(f"Location: {location_str}")
    if data.get("employmentType"):
        parts.append(f"Employment Type: {data['employmentType']}")
    if data.get("description"):
        desc_soup = BeautifulSoup(data["description"], "html.parser")
        parts.append(desc_soup.get_text(separator="\n", strip=True))
    return "\n\n".join(parts)


def _parse_soup(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    title = _text_from_soup(soup, TITLE_SELECTORS)
    company = _text_from_soup(soup, COMPANY_SELECTORS)
    location = _text_from_soup(soup, [".topcard__flavor--bullet", ".job-details-jobs-unified-top-card__bullet"])
    desc = _text_from_soup(soup, JD_SELECTORS)

    if desc:
        return "\n\n".join(filter(None, [title, company, location, desc]))

    # Full page fallback
    full_text = soup.get_text(separator="\n", strip=True)
    return full_text[:10000]


def scrape_linkedin_job(url: str) -> str:
    validate_url(url)
    job_id = extract_job_id(url)

    # Try guest API first (most reliable for public postings)
    if job_id:
        content = scrape_via_guest_api(job_id)
        if content and len(content) > 300:
            return content

    # Fall back to direct URL scraping
    content = scrape_via_direct_url(url)
    if not content or len(content) < 200:
        raise ValueError("Could not extract job description. The posting may require login or the URL may be invalid.")
    return content


def extract_jd(url: str) -> str:
    raw_text = scrape_linkedin_job(url)

    llm = ChatOpenAI(
        model="anthropic/claude-3.5-haiku",
        openai_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_base="https://openrouter.ai/api/v1",
        default_headers={"HTTP-Referer": "https://careerclaw.app"},
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=build_user_prompt(raw_text)),
    ]

    response = llm.invoke(messages)
    return response.content
