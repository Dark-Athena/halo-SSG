from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlparse

import httpx

from halo_ssg.utils.url import is_same_domain, normalize_url

logger = logging.getLogger("halo_ssg.crawler")


class AssetDownloader:
    def __init__(self, base_url: str, output_dir: Path, timeout: int = 30,
                 max_size_mb: int = 10, user_agent: str = "Halo-SSG/1.0"):
        self.base_url = base_url.rstrip("/")
        self.output_dir = output_dir
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": user_agent},
            follow_redirects=True,
        )
        self._downloaded: set[str] = set()
        self._failed: set[str] = set()

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> AssetDownloader:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def download_assets(self, urls: list[str]) -> dict[str, str]:
        mapping = {}
        for url in urls:
            abs_url = normalize_url(url, self.base_url)
            if abs_url in self._downloaded:
                mapping[url] = self._url_to_local_path(abs_url)
                continue
            if abs_url in self._failed:
                continue
            local_path = self._download_one(abs_url)
            if local_path:
                mapping[url] = local_path
        return mapping

    def _url_to_local_path(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed.path

    def _download_one(self, url: str) -> str | None:
        if not is_same_domain(url, self.base_url):
            return None

        parsed = urlparse(url)
        local_path = parsed.path.lstrip("/")
        output_path = self.output_dir / local_path

        if output_path.exists():
            self._downloaded.add(url)
            return "/" + local_path

        try:
            with self.client.stream("GET", url) as resp:
                resp.raise_for_status()
                content_length = int(resp.headers.get("content-length", 0))
                if content_length > self.max_size_bytes:
                    logger.warning(f"Skipping large asset ({content_length} bytes): {url}")
                    return None

                content_type = resp.headers.get("content-type", "")
                if not any(t in content_type for t in ["image", "javascript", "css", "font", "octet-stream", "svg"]):
                    if not local_path.endswith((".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
                                                ".css", ".js", ".woff", ".woff2", ".ttf", ".eot")):
                        logger.debug(f"Skipping non-asset: {url} (type: {content_type})")
                        return None

                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=8192):
                        f.write(chunk)

            self._downloaded.add(url)
            logger.debug(f"Downloaded: {local_path}")
            return "/" + local_path

        except Exception as e:
            self._failed.add(url)
            logger.warning(f"Failed to download {url}: {e}")
            return None
