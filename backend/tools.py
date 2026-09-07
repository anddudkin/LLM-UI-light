tools = [
    {
        "type": "function",
        "function": {
            "name": "web_search",  # Название функции, которое будет вызывать модель
            "description": "Ищет в интернете свежую информацию по заданному запросу. Используй этот инструмент, если тебе нужны данные, выходящие за рамки твоих знаний, или актуальная информация (новости, события, последние статьи)."
                           "Каждый результат поиска помечен ссылкой на источник. Если используешь эту информацию в ответе, ОБЯЗАТЕЛЬНО оформляй ссылку как markdown-ссылку в формате [название источника](URL) — никогда не пиши название сайта или статьи простым текстом без самой ссылки.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Поисковый запрос, сформулированный четко и конкретно, как для поисковой системы (например, 'последние новости искусственного интеллекта 2024' или 'погода в Москве на завтра')."
                    },
                },
                "required": ["query"]  # Обязательный параметр
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "company_data_search",  # Название функции, которое будет вызывать модель
            "description": "Ищет информацию во внутренней базе знаний компании. Используй этот инструмент, если тебе нужны данные о внутренних процессах (как взять отпуск, оформить заявление и т.д.), регламентах, документах или других подобных вещах компании.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Поисковый запрос, сформулированный четко и конкретно, как для поисковой системы."
                    },
                },
                "required": ["query"]  # Обязательный параметр
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

# Список User-Agent'ов остается таким же
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]


def _decode_html(raw: bytes) -> str:
    """
    Декодирует сырые байты страницы с автоопределением кодировки. Некоторые сайты отдают
    windows-1251/koi8-r без корректного charset в заголовках — aiohttp's response.text()
    в таком случае пытается декодировать как UTF-8 и падает с UnicodeDecodeError.
    """
    match = from_bytes(raw).best()
    if match is not None:
        return str(match)
    return raw.decode('utf-8', errors='replace')


async def fetch_page(session, url, semaphore):
    """
    Асинхронная загрузка одной страницы с использованием семафора
    для ограничения количества одновременных запросов
    """
    async with semaphore:  # Ограничиваем параллельные запросы
        try:
            headers = {'User-Agent': random.choice(user_agents)}

            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    raw = await response.read()
                    html = _decode_html(raw)

                    # Парсим HTML
                    soup = BeautifulSoup(html, 'html.parser')

                    # Удаляем ненужные элементы
                    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                        tag.decompose()

                    # Получаем текст
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
    Асинхронная обработка всех результатов поиска
    max_concurrent - максимальное количество одновременных запросов
    """
    # Создаем семафор для ограничения параллельных запросов
    semaphore = asyncio.Semaphore(max_concurrent)

    # Настраиваем сессию aiohttp
    timeout = aiohttp.ClientTimeout(total=15)
    connector = aiohttp.TCPConnector(limit=max_concurrent)  # Ограничиваем соединения

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        # Создаем задачи для всех URL
        tasks = []
        for result in search_results:
            url = result.get('href')
            if url:
                task = fetch_page(session, url, semaphore)
                tasks.append(task)

        # Запускаем все задачи параллельно и ждем их выполнения
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return results


def _ddgs_text(query, num_results):
    with DDGS() as ddgs:
        return list(ddgs.text(
            query,
            max_results=num_results,
            region='ru-ru'  # Добавляем регион для русских результатов
        ))


async def _searxng_text(query, num_results):
    """
    Поиск через внутренний инстанс SearXNG. Возвращает список в том же формате
    (title/href/body), что и _ddgs_text, чтобы дальнейшая сборка результатов не менялась.
    """
    if not SEARXNG_URL:
        raise RuntimeError("SEARXNG_URL не задан")

    headers = {'User-Agent': random.choice(user_agents)}
    params = {"q": query, "format": "json", "language": "ru"}
    timeout = aiohttp.ClientTimeout(total=SEARXNG_TIMEOUT)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(f"{SEARXNG_URL}/search", params=params, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()

    return [
        {"title": r.get("title") or "Без заголовка", "href": r.get("url"), "body": r.get("content", "")}
        for r in data.get("results", [])[:num_results]
    ]


async def web_search(query, num_results=5, max_concurrent=3):
    """
    Основная функция, запускающая асинхронный поиск и загрузку
    """
    try:
        search_results = await _searxng_text(query, num_results)
        logger.info(f"SearXNG нашёл результатов: {len(search_results)}")
    except Exception as e:
        logger.warning(f"SearXNG недоступен ({e}), переключаемся на DDGS для запроса '{query}'")
        search_results = None

    if not search_results:
        # search_results is None — SearXNG упал с ошибкой; search_results == [] — SearXNG
        # ответил, но ни один его движок не вернул результат (например, все получили капчу).
        # В обоих случаях пробуем DDGS как резервный источник.
        if search_results is not None:
            logger.warning(f"SearXNG не нашёл результатов для '{query}', переключаемся на DDGS")
        # DDGS синхронный, поэтому выносим его в отдельный поток, чтобы не блокировать event loop
        try:
            search_results = await asyncio.to_thread(_ddgs_text, query, num_results)
        except Exception as e2:
            logger.error(f"Ошибка поиска DDGS по запросу '{query}': {e2}")
            return "Поиск в интернете временно недоступен, попробуйте переформулировать запрос или повторить позже."

    logger.info(f"Найдено результатов: {len(search_results)}")

    if not search_results:
        logger.info("Ничего не найдено")
        return "По запросу ничего не найдено."

    # 2. Запускаем асинхронную загрузку страниц
    logger.info(f"Загружаем страницы (макс. {max_concurrent} одновременно)...")
    start_time = time.time()

    page_results = await process_results(search_results, max_concurrent)

    elapsed = time.time() - start_time
    logger.info(f"Загрузка заняла {elapsed:.2f} секунд")
    full_text = ""
    # 3. Собираем результаты
    for i, (search_result, page_result) in enumerate(zip(search_results, page_results), 1):
        title = search_result.get('title', 'Без заголовка')
        url = search_result.get('href')

        full_text += f"\n [{i}] {title}"
        full_text += f" {url}"

        if isinstance(page_result, dict) and page_result.get('success'):
            text = page_result['text']
            logger.info(f"[{i}] Полный текст получен ({len(text)} символов)")
            full_text += " " + text[:SEARCH_PAGE_CHAR_LIMIT]
        else:
            error_msg = page_result.get('error') if isinstance(page_result, dict) else str(page_result)
            logger.info(f"[{i}] Не удалось загрузить страницу: {error_msg}")
            # Страница не загрузилась - используем сниппет, который уже вернул DDGS
            snippet = search_result.get('body', '')
            if snippet:
                full_text += " " + snippet
    return full_text