from .tool_registery import tool
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

@tool("Use this tool to fetch the latest news from Yahoo news", {"topic": {
                "type": "string",
                "description": "The search query for the news you want to fetch. For example, if you want to fetch the latest news about Apple Inc., you can use 'Apple Inc.' as the topic."
            }})
def get_latest_news(topic):
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


@tool("Use this tool to access and fetch the text content of a web page given its known URL.", {"url": {
                "type": "string",
                "description": "The URL of the web page you want to access. For example, 'https://www.bbc.com/news/world-us-canada-66231848'."
            }})
def access_web_url(url):
    print(f"Accessing URL: {url}")
    headers= {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    response = requests.get(url, headers=headers)
    html = response.text
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    elements = soup.find_all(["h1", "h2","h3" "p"])
    texts = [el.get_text(strip=True) for el in elements[:25]]
    return "\n".join(texts)
 