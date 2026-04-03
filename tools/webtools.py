from .tool_registery import tool
import requests
from bs4 import BeautifulSoup


@tool("Use this tool to fetch the latest news from Yahoo news", {"topic": {
                "type": "string",
                "description": "The search query for the news you want to fetch. For example, if you want to fetch the latest news about Apple Inc., you can use 'Apple Inc.' as the topic."
            }})
def get_latest_news(topic):
    headers= {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referrer': 'https://search.yahoo.com/search'
    }
    print(f"Fetching news for topic: {topic}")
    url = f"https://news.search.yahoo.com/search?p={topic}"
    response = requests.get(url, headers=headers)
    html = response.text
    soup = BeautifulSoup(html, "html.parser")
    news_items = soup.select("ol.searchCenterMiddle li")
    news=''
    for item in news_items[::2]:
        a = item.select_one("a")
        title = a["title"]
        source = item.select_one("span.s-source").text if item.select_one("span.s-source") else "Unknown source"
        time = item.select_one("span.s-time").text if item.select_one("span.s-time") else "Unknown time"
        news += f"Title: {title}\nSource: {source}\nTime: {time}\n\n"
    print(f"Fetched news:\n{news}")
    return news


@tool("Use this tool to access and fetch the text content of a web page given its URL.", {"url": {
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
 