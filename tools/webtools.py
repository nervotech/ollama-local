from .tool_registery import tool
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, urljoin, urlparse

@tool("Use this tool to fetch realtime information from Yahoo", {"topic": {
                "type": "string",
                "description": "The short search query for the information you want to fetch. For example, if you want to fetch the latest information about Apple Inc., you can use 'Apple Inc.' as the topic."
            }})
def web_search(topic):
    topic = quote(topic)
    headers= {
         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    print(f"Fetching news for topic: {topic}")
    url = f"https://www.bing.com/news/search?q={topic}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    results = ""
    articles = soup.select("div.news-card-body")

    for article in articles:
        caption = article.select_one("div.caption")
        title_tag = caption.select_one("a.title h2")
        link_tag = article.find("a", href=True)

        title = title_tag.get_text(strip=True) if title_tag else None
        link = link_tag["href"] if link_tag else None

        # Optional description
        desc_tag = caption.select_one("div.snippet")
        description = desc_tag.get_text(strip=True) if desc_tag else None

        results += f"Title: {title}\nLink: {link}\nDescription: {description}\n\n"
    return results


@tool("""Fetch and extract readable text content from a publicly accessible web page.
The tool downloads the page, removes script and style content, and extracts text and links.

Use this tool when you need to inspect, summarize, or retrieve textual information from a specific web page URL. Do not use it for pages that require authentication or when a specialized API or tool is more appropriate.""", {"url": {
                "type": "string",
                "description": "The URL of the web page you want to access. For example, 'https://www.bbc.com/news/world-us-canada-66231848'."
            },
            "crawl": {
                "type": "boolean",
                "description": "Whether you want to crawl the page for further links to follow. This helps if you need to dive deep into the website. "
            }})

def fetch_url(url, headers=None, timeout=15, crawl=False, max_depth=2):
    """
    Fetch a web page and return a structured summary.

    Returns dict: {"status": int, "text": str, "links": [{url, text}], "subpages": [...]}
    """
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
                 "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    headers = {
        "User-Agent": user_agent,
        "Accept-Language": "en-US,en;q=0.9",
    }
    if headers:
        headers.update(headers)

    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()

    # --- Extract links from the page (the key new capability) ---
    soup = BeautifulSoup(response.text, "html.parser")
    links = []
    for tag in soup(["script", "style"]):
            tag.decompose()
    text =  soup.get_text()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        links.append({"url": href, "text": a.get_text(strip=True)})
    
    # --- Optional recursive crawl ---
    subpages = []
    if crawl:
        seen = {urlparse(url).netloc}
        stack = [(url, 0)]
        while stack:
            page_url, depth = stack.pop()
            try:
                sub_resp = requests.get(page_url, headers=headers, timeout=timeout)
                sub_resp.raise_for_status()
                sub_soup = BeautifulSoup(sub_resp.text, "html.parser")
                for a in sub_soup.find_all("a", href=True):
                    href = a["href"].strip()
                    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                        continue
                    target = urljoin(page_url, href)
                    netloc = urlparse(target).netloc
                    if netloc not in seen and depth < max_depth:
                        seen.add(netloc)
                        subpages.append(target)
                        stack.append((target, depth + 1))
            except requests.RequestException:
                continue  # skip pages that fail; don't crash the crawl

    return {
        "status": response.status_code,
        "links": links,
        "text": text,
        "subpages": subpages,
    }


def get_text(url, headers=None, timeout=15):
    """Backward-compatible: returns cleaned readable text (original behavior)."""
    result = fetch_url(url, headers=headers, timeout=timeout)
    if result["status"] != 200:
        raise RuntimeError(f"Failed to fetch {url}: HTTP {result['status']}")
    soup = BeautifulSoup(result["text"], "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text()