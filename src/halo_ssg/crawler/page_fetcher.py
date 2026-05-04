from __future__ import annotations

import logging
import time

import httpx

from halo_ssg.exceptions import CrawlError

logger = logging.getLogger("halo_ssg.crawler")


class PageFetcher:
    def __init__(self, base_url: str, rate_limit: float = 2.0, timeout: int = 30,
                 max_retries: int = 3, user_agent: str = "Halo-SSG/1.0"):
        self.base_url = base_url.rstrip("/")
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self.client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": user_agent},
            follow_redirects=True,
        )
        self._last_request_time = 0.0

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> PageFetcher:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def _wait_rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)

    def fetch(self, path: str) -> str:
        url = f"{self.base_url}{path}"
        for attempt in range(self.max_retries):
            self._wait_rate_limit()
            try:
                self._last_request_time = time.time()
                resp = self.client.get(url)
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
                    wait = 2 ** (attempt + 1)
                    logger.warning(f"HTTP {e.response.status_code} on {path}, retry in {wait}s...")
                    time.sleep(wait)
                    continue
                raise CrawlError(f"HTTP {e.response.status_code} for {path}") from e
            except httpx.RequestError as e:
                if attempt < self.max_retries - 1:
                    wait = 2 ** (attempt + 1)
                    logger.warning(f"Request error on {path}, retry in {wait}s: {e}")
                    time.sleep(wait)
                    continue
                raise CrawlError(f"Request failed for {path}: {e}") from e
        raise CrawlError(f"Failed after retries: {path}")
