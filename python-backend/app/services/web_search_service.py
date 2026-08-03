import base64
import html as html_lib
import json
import re
import time
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from urllib import error, parse, request

from app.config import settings


DEFAULT_MAX_RESULTS = 5
MAX_RESULTS_LIMIT = 10
TAVILY_SEARCH_URL = "https://api.tavily.com/search"
BING_SEARCH_URL = "https://cn.bing.com/search"


@dataclass
class WebSearchResult:
    title: str
    url: str
    content: str
    score: float | None = None
    published_date: str | None = None
    source: str | None = None

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "score": self.score,
            "publishedDate": self.published_date,
            "source": self.source,
        }


class TavilyWebSearchClient:
    def __init__(self, api_key: str | None = None, timeout: int | None = None):
        self.api_key = (api_key if api_key is not None else settings.tavily_api_key).strip()
        self.timeout = int(timeout if timeout is not None else settings.web_search_timeout)

    def search(
        self,
        query: str,
        *,
        max_results: int = DEFAULT_MAX_RESULTS,
        topic: str = "general",
        start_date: str | None = None,
        end_date: str | None = None,
        country: str | None = None,
    ) -> dict:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("Web search query cannot be empty")
        if not self.api_key:
            raise RuntimeError("TAVILY_API_KEY is not configured; web_search cannot access live news.")

        started = time.perf_counter()
        payload = {
            "query": normalized_query,
            "search_depth": "basic",
            "max_results": max(1, min(int(max_results or DEFAULT_MAX_RESULTS), MAX_RESULTS_LIMIT)),
            "topic": topic if topic in {"general", "news"} else "general",
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
            "include_favicon": False,
            "safe_search": True,
        }
        if start_date:
            payload["start_date"] = start_date
        if end_date:
            payload["end_date"] = end_date
        if country:
            payload["country"] = country

        try:
            with request.urlopen(self._request(payload), timeout=self.timeout) as response:
                status = getattr(response, "status", 200)
                body = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = self._read_error_detail(exc)
            raise RuntimeError(f"Tavily web search failed ({exc.code}): {detail}") from exc
        except error.URLError as exc:
            raise ConnectionError("Unable to reach Tavily web search API") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("Tavily web search returned invalid JSON") from exc

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "provider": "tavily",
            "status": status,
            "query": body.get("query") or normalized_query,
            "topic": payload["topic"],
            "startDate": start_date,
            "endDate": end_date,
            "elapsedMs": elapsed_ms,
            "results": [item.to_dict() for item in self._parse_results(body.get("results") or [])],
        }

    def _request(self, payload: dict) -> request.Request:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return request.Request(
            TAVILY_SEARCH_URL,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

    @staticmethod
    def _parse_results(rows: list[dict]) -> list[WebSearchResult]:
        results: list[WebSearchResult] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or "").strip()
            url = str(row.get("url") or "").strip()
            content = str(row.get("content") or "").strip()
            if not title or not url:
                continue
            results.append(
                WebSearchResult(
                    title=title,
                    url=url,
                    content=content,
                    score=row.get("score") if isinstance(row.get("score"), (int, float)) else None,
                    published_date=(
                        str(row.get("published_date")).strip()
                        if row.get("published_date") is not None
                        else None
                    ),
                    source=str(row.get("source")).strip() if row.get("source") else None,
                )
            )
        return results

    @staticmethod
    def _read_error_detail(exc: error.HTTPError) -> str:
        try:
            body = json.loads(exc.read().decode("utf-8"))
            detail = body.get("detail") if isinstance(body, dict) else None
            if isinstance(detail, dict):
                return str(detail.get("error") or detail)
            return str(detail or body)
        except Exception:
            return exc.reason or "unknown error"


class BingWebSearchClient:
    """Free web search via cn.bing.com HTML results. No API key required.

    Works from mainland China without a proxy. Used as the default provider,
    and as an automatic fallback when Tavily is not configured or fails.
    """

    def __init__(self, timeout: int | None = None):
        self.timeout = int(timeout if timeout is not None else settings.web_search_timeout)

    def search(self, query: str, *, max_results: int = DEFAULT_MAX_RESULTS, topic: str = "general") -> dict:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("Web search query cannot be empty")

        started = time.perf_counter()
        params = {
            "q": normalized_query,
            "count": max(1, min(int(max_results or DEFAULT_MAX_RESULTS), MAX_RESULTS_LIMIT)),
            "setlang": "zh-hans",
            "mkt": "zh-CN",
        }
        url = f"{BING_SEARCH_URL}?{parse.urlencode(params)}"
        req = request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                ),
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
            method="GET",
        )
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with request.urlopen(req, timeout=self.timeout) as response:
                    status = getattr(response, "status", 200)
                    body = response.read().decode("utf-8", errors="replace")
                    break
            except (error.HTTPError, error.URLError) as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(0.8 * (attempt + 1))
        else:
            if isinstance(last_error, error.HTTPError):
                raise RuntimeError(f"Bing web search failed ({last_error.code})") from last_error
            raise ConnectionError("Unable to reach Bing web search") from last_error

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "provider": "bing",
            "status": status,
            "query": normalized_query,
            "topic": topic,
            "startDate": None,
            "endDate": None,
            "elapsedMs": elapsed_ms,
            "results": [item.to_dict() for item in self._parse_results(body)],
        }

    @staticmethod
    def _parse_results(body: str) -> list[WebSearchResult]:
        parser = _BingResultParser()
        try:
            parser.feed(body)
        except Exception:
            return []
        results: list[WebSearchResult] = []
        for title, url, content in parser.results:
            if not title or not url:
                continue
            results.append(
                WebSearchResult(
                    title=html_lib.unescape(title),
                    url=BingWebSearchClient._decode_bing_url(url),
                    content=html_lib.unescape(content or "")[:500],
                )
            )
        return results

    @staticmethod
    def _decode_bing_url(href: str) -> str:
        """Bing wraps result links in /ck/a?u=<base64url>. Decode when possible."""
        try:
            parsed = parse.urlparse(href)
            if "ck/a" not in parsed.path:
                return href
            params = parse.parse_qs(parsed.query)
            encoded = (params.get("u") or [""])[0]
            if not encoded:
                return href
            padded = encoded + "=" * (-len(encoded) % 4)
            decoded = base64.urlsafe_b64decode(padded).decode("utf-8", errors="ignore")
            return decoded if decoded.startswith(("http://", "https://")) else href
        except Exception:
            return href


class _BingResultParser(HTMLParser):
    """Extract (title, url, snippet) triples from Bing <li class="b_algo"> blocks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.results: list[tuple[str, str, str]] = []
        self._in_algo = False
        self._algo_depth = 0
        self._in_title = False
        self._in_snippet = False
        self._title_parts: list[str] = []
        self._snippet_parts: list[str] = []
        self._title_href = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        classes = (attrs_dict.get("class") or "").split()
        if tag == "li" and "b_algo" in classes:
            self._in_algo = True
            self._algo_depth = 0
            self._title_parts = []
            self._snippet_parts = []
            self._title_href = ""
            return
        if not self._in_algo:
            return
        self._algo_depth += 1
        if tag == "h2" and (not classes or "b_title" in classes):
            self._in_title = True
        if tag == "a" and self._in_title:
            for key, value in attrs:
                if key == "href" and value and not self._title_href:
                    self._title_href = value
        if tag == "p" and not self._in_snippet:
            self._in_snippet = True

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)
        elif self._in_snippet:
            self._snippet_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self._in_algo:
            return
        if tag == "h2":
            self._in_title = False
        elif tag == "p":
            self._in_snippet = False
        elif tag == "li":
            if self._title_parts:
                self.results.append(
                    (
                        "".join(self._title_parts).strip(),
                        self._title_href,
                        "".join(self._snippet_parts).strip(),
                    )
                )
            self._in_algo = False
        self._algo_depth = max(0, self._algo_depth - 1)


class WebSearchService:
    def __init__(self, provider: str | None = None):
        self.provider = (provider or settings.web_search_provider or "bing").lower()

    def search(
        self,
        query: str,
        *,
        max_results: int = DEFAULT_MAX_RESULTS,
        topic: str = "general",
        date_scope: str | None = None,
        country: str | None = None,
    ) -> dict:
        start_date, end_date = self._date_range(date_scope)
        if self.provider == "bing":
            return BingWebSearchClient().search(query, max_results=max_results, topic=topic)
        if self.provider == "tavily":
            try:
                return TavilyWebSearchClient().search(
                    query,
                    max_results=max_results,
                    topic=topic,
                    start_date=start_date,
                    end_date=end_date,
                    country=country,
                )
            except RuntimeError:
                # No API key configured, or the API call failed: fall back to free Bing.
                return BingWebSearchClient().search(query, max_results=max_results, topic=topic)
        raise RuntimeError(f"Unsupported web search provider: {self.provider}")

    @staticmethod
    def _date_range(date_scope: str | None) -> tuple[str | None, str | None]:
        if not date_scope:
            return None, None
        normalized = date_scope.strip().lower()
        if normalized in {"today", "current_date"}:
            today = date.today().isoformat()
            return today, today
        if len(normalized) == 10 and normalized[4] == "-" and normalized[7] == "-":
            return normalized, normalized
        return None, None
