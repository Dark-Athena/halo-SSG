from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from halo_ssg.exceptions import CrawlError

logger = logging.getLogger("halo_ssg.crawler")


class PageFetcher:
    def __init__(self, base_url: str, rate_limit: float = 2.0, timeout: int = 30,
                 max_retries: int = 3, user_agent: str = "Halo-SSG/1.0",
                 concurrency: int = 5):
        self.base_url = base_url.rstrip("/")
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self.timeout = timeout
        self.user_agent = user_agent
        self.concurrency = max(1, concurrency)

    def close(self) -> None:
        pass

    def __enter__(self) -> PageFetcher:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def _create_client(self) -> httpx.Client:
        return httpx.Client(
            timeout=self.timeout,
            headers={"User-Agent": self.user_agent},
            follow_redirects=True,
        )

    def fetch(self, path: str) -> str:
        url = f"{self.base_url}{path}"
        client = self._create_client()
        try:
            for attempt in range(self.max_retries):
                try:
                    resp = client.get(url)
                    resp.raise_for_status()
                    return resp.text
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        wait = int(e.response.headers.get("Retry-After", 60))
                        logger.warning(f"Rate limited on {path}, waiting {wait}s...")
                        time.sleep(wait)
                        continue
                    if e.response.status_code == 404:
                        logger.warning(f"Page not found: {path}")
                        return ""
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** (attempt + 1))
                        continue
                    raise CrawlError(f"HTTP {e.response.status_code} for {path}") from e
                except httpx.RequestError as e:
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** (attempt + 1))
                        continue
                    raise CrawlError(f"Request failed for {path}: {e}") from e
            raise CrawlError(f"Failed after retries: {path}")
        finally:
            client.close()

    def fetch_many(self, paths: list[str], progress_callback=None) -> dict[str, str]:
        results = {}
        delay = self.rate_limit / self.concurrency

        def _fetch_one(path: str) -> tuple[str, str]:
            time.sleep(delay)
            return path, self.fetch(path)

        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            futures = {executor.submit(_fetch_one, p): p for p in paths}
            for future in as_completed(futures):
                path, html = future.result()
                results[path] = html
                if progress_callback:
                    progress_callback()

        return results
