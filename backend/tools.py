tools = [
    {
        "type": "function",
        "function": {
            "name": "web_search",  # Name of the function the model will call
            "description": "Searches the internet for up-to-date information on a given query. Use this tool when you need data beyond your own knowledge, or current information (news, events, recent articles)."
                           "Every search result is tagged with a source link. If you use this information in your answer, you MUST format the link as a markdown link in the format [source name](URL) — never write the site or article name as plain text without the link itself.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A search query phrased clearly and specifically, as you would for a search engine (e.g. 'latest artificial intelligence news 2024' or 'weather in London tomorrow')."
                    },
                },
                "required": ["query"]  # Required parameter
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "company_data_search",  # Name of the function the model will call
            "description": "Searches the company's internal knowledge base. Use this tool when you need information about internal processes (how to request time off, submit a form, etc.), policies, documents, or other similar company-specific matters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A search query phrased clearly and specifically, as you would for a search engine."
                    },
                },
                "required": ["query"]  # Required parameter
            }
        }
    }
]


import asyncio
import logging
import os
import aiohttp
import random
from bs4 import BeautifulSoup
from charset_normalizer import from_bytes
from ddgs import DDGS
import time

logger = logging.getLogger(__name__)

# Primary web-search backend, an internal SearXNG instance (see docker-compose.yml). If unset,
# unreachable, or erroring, web_search() falls back to the ddgs library below.
SEARXNG_URL = os.environ.get("SEARXNG_URL")
# Timeout (seconds) for the single SearXNG search request. On timeout, web_search() falls back
# to ddgs the same as any other SearXNG failure.
SEARXNG_TIMEOUT = float(os.environ.get("SEARXNG_TIMEOUT", "5"))
# Max characters of extracted page text kept per search result before it's handed to the model.
SEARCH_PAGE_CHAR_LIMIT = int(os.environ.get("SEARCH_PAGE_CHAR_LIMIT", "1500"))

# List of User-Agents stays the same
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]


def _decode_html(raw: bytes) -> str:
    """
    Decodes the page's raw bytes with automatic encoding detection. Some sites serve
    windows-1251/koi8-r content without a correct charset in their headers — aiohttp's
    response.text() would try to decode it as UTF-8 in that case and raise UnicodeDecodeError.
    """
    match = from_bytes(raw).best()
    if match is not None:
        return str(match)
    return raw.decode('utf-8', errors='replace')


async def fetch_page(session, url, semaphore):
    """
    Asynchronously fetches a single page, using a semaphore to limit the number
    of concurrent requests
    """
    async with semaphore:  # Limit concurrent requests
        try:
            headers = {'User-Agent': random.choice(user_agents)}

            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    raw = await response.read()
                    html = _decode_html(raw)

                    # Parse the HTML
                    soup = BeautifulSoup(html, 'html.parser')

                    # Remove unwanted elements
                    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                        tag.decompose()

                    # Extract the text
                    full_text = soup.get_text()
                    full_text = ' '.join(full_text.split())

                    return {
                        'success': True,
                        'text': full_text,
                        'url': url
                    }
                else:
                    return {
                        'success': False,
                        'error': f"HTTP {response.status}",
                        'url': url
                    }

        except asyncio.TimeoutError:
            return {'success': False, 'error': 'Timeout', 'url': url}
        except Exception as e:
            return {'success': False, 'error': str(e), 'url': url}


async def process_results(search_results, max_concurrent=3):
    """
    Asynchronously processes all search results
    max_concurrent - maximum number of concurrent requests
    """
    # Create a semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(max_concurrent)

    # Configure the aiohttp session
    timeout = aiohttp.ClientTimeout(total=15)
    connector = aiohttp.TCPConnector(limit=max_concurrent)  # Limit connections

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        # Create tasks for all URLs
        tasks = []
        for result in search_results:
            url = result.get('href')
            if url:
                task = fetch_page(session, url, semaphore)
                tasks.append(task)

        # Run all tasks concurrently and wait for them to finish
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return results


def _ddgs_text(query, num_results):
    with DDGS() as ddgs:
        return list(ddgs.text(
            query,
            max_results=num_results,
            region='us-en'  # Region for English-language results
        ))


async def _searxng_text(query, num_results):
    """
    Searches via the internal SearXNG instance. Returns a list in the same format
    (title/href/body) as _ddgs_text, so downstream result assembly doesn't need to change.
    """
    if not SEARXNG_URL:
        raise RuntimeError("SEARXNG_URL is not set")

    headers = {'User-Agent': random.choice(user_agents)}
    params = {"q": query, "format": "json", "language": "en"}
    timeout = aiohttp.ClientTimeout(total=SEARXNG_TIMEOUT)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(f"{SEARXNG_URL}/search", params=params, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()

    return [
        {"title": r.get("title") or "Untitled", "href": r.get("url"), "body": r.get("content", "")}
        for r in data.get("results", [])[:num_results]
    ]


async def web_search(query, num_results=5, max_concurrent=3):
    """
    Main function that runs the asynchronous search and page fetch
    """
    try:
        search_results = await _searxng_text(query, num_results)
        logger.info(f"SearXNG found results: {len(search_results)}")
    except Exception as e:
        logger.warning(f"SearXNG unavailable ({e}), falling back to DDGS for query '{query}'")
        search_results = None

    if not search_results:
        # search_results is None — SearXNG raised an error; search_results == [] — SearXNG
        # responded, but none of its engines returned a result (e.g. all got CAPTCHA'd).
        # In both cases, try DDGS as a fallback source.
        if search_results is not None:
            logger.warning(f"SearXNG found no results for '{query}', falling back to DDGS")
        # DDGS is synchronous, so run it in a separate thread to avoid blocking the event loop
        try:
            search_results = await asyncio.to_thread(_ddgs_text, query, num_results)
        except Exception as e2:
            logger.error(f"DDGS search error for query '{query}': {e2}")
            return "Web search is temporarily unavailable, try rephrasing your query or try again later."

    logger.info(f"Found results: {len(search_results)}")

    if not search_results:
        logger.info("Nothing found")
        return "No results were found for this query."

    # 2. Asynchronously fetch the pages
    logger.info(f"Fetching pages (max {max_concurrent} concurrently)...")
    start_time = time.time()

    page_results = await process_results(search_results, max_concurrent)

    elapsed = time.time() - start_time
    logger.info(f"Fetching took {elapsed:.2f} seconds")
    full_text = ""
    # 3. Assemble the results
    for i, (search_result, page_result) in enumerate(zip(search_results, page_results), 1):
        title = search_result.get('title', 'Untitled')
        url = search_result.get('href')

        full_text += f"\n [{i}] {title}"
        full_text += f" {url}"

        if isinstance(page_result, dict) and page_result.get('success'):
            text = page_result['text']
            logger.info(f"[{i}] Full text retrieved ({len(text)} characters)")
            full_text += " " + text[:SEARCH_PAGE_CHAR_LIMIT]
        else:
            error_msg = page_result.get('error') if isinstance(page_result, dict) else str(page_result)
            logger.info(f"[{i}] Failed to fetch page: {error_msg}")
            # The page failed to load - use the snippet already returned by DDGS
            snippet = search_result.get('body', '')
            if snippet:
                full_text += " " + snippet
    return full_text