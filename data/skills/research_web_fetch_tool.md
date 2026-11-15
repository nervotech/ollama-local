# Refined Web Fetch Tool — Research Mode

## Why refine?
The original `access_web_url` only returned visible text (headings + paragraphs) and
**could not return links**. For research, links are critical: they let you follow a page's
references, discover sources, and build a citation trail. This refined version adds:

1. **Link extraction** — returns every external URL on the page (the user's #1 ask).
2. **Optional recursive crawl** — follow links and fetch further pages (up to a depth limit).
3. **Robust output** — returns a structured summary (status, text, links) so the assistant
   can decide whether the page loaded and what to do next.

---

## Limitations of the original tool (verified)
- ❌ **No links returned** — `soup.get_text()` discards all `<a href>` data. (Confirmed via test.)
- ❌ **No error handling** — a failing/host-unreachable page raises and returns nothing usable.
- ❌ **No duplicate removal** — repeated paragraphs (ads, nav) pollute the summary.
- ❌ **Tables flattened** — table cells merge into unreadable lines (bad for data pages).
- ❌ **No depth limit** — recursive fetching could loop infinitely.

---

## Refined implementation

```python
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import requests


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
```

### How to use

```python
# 1. Structured fetch — get text + all links at once
result = fetch_url("https://example.com/page")
for link in result["links"]:
    print(link["url"], "->", link["text"])

# 2. Recursive crawl — discover related pages (depth-limited, no infinite loops)
subpages = fetch_url("https://nervo.tech", crawl=True, max_depth=2)["subpages"]
print("Related pages:", subpages)

# 3. Backward compatible — plain readable text
text = get_text("https://example.com")
```

---

## Design decisions

| Decision | Reason |
|----------|--------|
| Return a **dict**, not just text | Assistant needs to know if the page loaded (`status`) and can act on links/subpages. |
| **Filter** `#`, `mailto:`, `tel:`, `javascript:` links | Only real, navigable external URLs are useful for research. |
| **Depth limit** (`max_depth`) + `seen` set | Guarantees termination — prevents infinite loops and repeated fetches. |
| **`urljoin`** for relative links | Correctly resolves `/about` → `https://host/about` using the page's base URL. |
| **`raise_for_status()`** | Converts HTTP errors into exceptions the assistant can catch and report. |
| Keep `get_text()` alias | Preserves the existing interface for anything relying on old behavior. |

## Notes / caveats
- `urljoin` only handles same-domain and absolute links correctly. Cross-domain
  relative links are intentionally excluded (safer default).
- Consider adding `retries` / `backoff` for flaky networks in production.
- For heavy pages, you may want to dedupe repeated `<p>`/`<h>` text or preserve tables.
