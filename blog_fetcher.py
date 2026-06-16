

import os
import json
from datetime import datetime, timedelta
from tavily import TavilyClient
from dotenv import load_dotenv
from LLM_Inference import llm_call

load_dotenv()

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

BLOG_SOURCES = {
    "OpenAI": "https://openai.com/blog",
    "Anthropic News": "https://www.anthropic.com/news",
    "Anthropic Engineering": "https://www.anthropic.com/engineering",
    "Anthropic Research": "https://www.anthropic.com/research",
    "Google DeepMind": "https://deepmind.google/blog",
    "Meta AI": "https://ai.meta.com/blog",
    "Mistral AI": "https://mistral.ai/news",
    "NVIDIA": "https://blogs.nvidia.com",
    "NVIDIA Technical": "https://developer.nvidia.com/blog",
    "Hugging Face": "https://huggingface.co/blog",
    "Together AI": "https://www.together.ai/blog",
    "Cohere": "https://cohere.com/blog",
    "Apple ML": "https://machinelearning.apple.com",
    "Allen AI": "https://allenai.org/blog",
    "Uber Engineering": "https://www.uber.com/en-US/blog/engineering",
}

SYSTEM_PROMPT = """You are a blog post extractor. Today is {today}.

I'll give you raw content extracted from AI company blog listing pages. 
Parse out individual blog posts and return them as a JSON array.

For each post, extract:
- "title": the blog post title
- "url": full URL to the blog post (construct from relative paths if needed)
- "published_date": the date shown (e.g. "Apr 08, 2026"), or "Recent" if not visible
- "source": the company name

Rules:
- Only include posts from the LAST 2 MONTHS (after {two_months_ago})
- Skip posts with no clear title or URL
- Skip navigation links, footer links, category pages
- If a URL is relative (like /news/some-post), prepend the site's base URL
- Remove trailing metadata from titles (like "| OpenAI", "- Anthropic", etc.)
- Include ALL qualifying posts — do not be selective, include everything recent

Return ONLY the JSON array. No other text."""


def fetch_blogs(extra_sources: dict[str, str] | None = None) -> list[dict]:
    """Extract blog posts directly from company blog listing pages."""
    today = datetime.now()
    two_months_ago = today - timedelta(days=60)

    sources = dict(BLOG_SOURCES)
    if extra_sources:
        sources.update(extra_sources)

    urls = list(sources.values())

    # Tavily extract supports up to 20 URLs per call
    all_content = []
    for i in range(0, len(urls), 20):
        batch = urls[i:i + 20]
        try:
            result = tavily_client.extract(urls=batch)
            for r in result.get("results", []):
                source_name = _url_to_source(r.get("url", ""), sources)
                raw = r.get("raw_content", "")
                cleaned = _strip_boilerplate(raw)
                all_content.append({
                    "source": source_name,
                    "url": r.get("url", ""),
                    "content": cleaned[:8000],
                })
            failed = result.get("failed_results", [])
            if failed:
                print(f"[extract] Failed URLs: {[f.get('url','') for f in failed]}")
        except Exception as e:
            print(f"[extract] Error: {e}")

    print(f"[extract] Got content from {len(all_content)}/{len(urls)} blog pages")

    if not all_content:
        return []

    extract_text = ""
    for item in all_content:
        extract_text += f"\n--- SOURCE: {item['source']} (from {item['url']}) ---\n"
        extract_text += item["content"]
        extract_text += "\n"

    formatted_prompt = SYSTEM_PROMPT.format(
        today=today.strftime("%Y-%m-%d"),
        two_months_ago=two_months_ago.strftime("%Y-%m-%d"),
    )

    try:
        llm_response = llm_call(
            system_prompt=formatted_prompt,
            user_prompt=f"Blog page contents:\n{extract_text}",
        )

        clean = llm_response.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1]
            clean = clean.rsplit("```", 1)[0]

        blogs = json.loads(clean)
        print(f"[llm] Extracted {len(blogs)} blog posts")
        return blogs

    except (json.JSONDecodeError, Exception) as e:
        print(f"[llm] Error: {e}")
        return []


def _strip_boilerplate(raw: str) -> str:
    """Strip nav headers, footers, image refs, and markdown noise to maximize blog post data."""
    import re
    lines = raw.split("\n")

    kept = []
    for line in lines:
        if line.startswith("*   [") and "](" in line:
            continue
        if re.match(r"^\s*\*\s*$", line):
            continue
        if line.startswith("![Image"):
            continue
        if "Skip to" in line:
            continue
        if line.startswith("*   *"):
            continue
        kept.append(line)

    text = "\n".join(kept)
    text = re.sub(r"\[!\[Image \d+\]\([^)]*\)\s*", "[", text)
    text = re.sub(r"\* !\[Image \d+\]\([^)]*\)\s*", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _url_to_source(url: str, sources: dict[str, str]) -> str:
    for name, base_url in sources.items():
        if base_url.rstrip("/") in url:
            return name
    return "Unknown"
